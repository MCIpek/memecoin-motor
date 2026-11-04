from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from time import monotonic
import time
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .config import Settings
from .gaps import SlotTracker
from .models import ChainEvent, SlotGap, TokenObservation, utc_now_iso
from .parser import is_pump_creation_logs, transaction_mentions_program
from .pump_decoder import (
    PumpDecodeError,
    PumpLaunch,
    decode_pump_launch,
    decode_pump_trade_logs,
)
from .paper import PaperAssumptions
from .paper_engine import run_paper_cycle
from .rpc import RpcError, SolanaRpc
from .scoring import score_snapshots
from .sniper import score_snipers
from .storage import Storage
from .transaction_analysis import analyze_transaction
from .wallet_analysis import FundingTransfer, inbound_system_transfers

logger = logging.getLogger(__name__)


class CollectorService:
    def __init__(self, settings: Settings, storage: Storage):
        if not settings.launch_program_id:
            raise ValueError("LAUNCH_PROGRAM_ID ayarlanmadan collector baslatilamaz")
        self.settings = settings
        self.storage = storage
        self.provider = urlparse(settings.solana_http_url).netloc or "unknown"
        self.slot_tracker = SlotTracker(storage.get_state_int("last_observed_slot"))
        self._gap_queue: asyncio.Queue[tuple[int, int]] = asyncio.Queue()
        self._launch_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=5000)
        # Onceki process kapanisindan sonra kalan sureyi eksiksiz varsayma.
        storage.end_snapshot_tracking(int(time.time()))
        self._tracked_launches = storage.tracked_launches()

    async def run(self) -> None:
        async with SolanaRpc(
            self.settings.solana_http_url, self.settings.rpc_timeout_seconds
        ) as rpc:
            backfill = asyncio.create_task(self._backfill_worker(rpc))
            launches = asyncio.create_task(self._launch_transaction_worker(rpc))
            snapshots = asyncio.create_task(self._snapshot_worker())
            wallet_worker = (
                asyncio.create_task(self._wallet_analysis_worker(rpc))
                if self.settings.wallet_enrichment_enabled else None
            )
            paper_worker = (
                asyncio.create_task(self._paper_worker())
                if self.settings.paper_enabled else None
            )
            sniper_worker = (
                asyncio.create_task(self._sniper_enrichment_worker(rpc))
                if self.settings.sniper_enabled else None
            )
            try:
                await self._reconnecting_stream(rpc)
            finally:
                backfill.cancel()
                snapshots.cancel()
                launches.cancel()
                tasks = [backfill, launches, snapshots]
                if wallet_worker:
                    wallet_worker.cancel()
                    tasks.append(wallet_worker)
                if paper_worker:
                    paper_worker.cancel()
                    tasks.append(paper_worker)
                if sniper_worker:
                    sniper_worker.cancel()
                    tasks.append(sniper_worker)
                await asyncio.gather(*tasks, return_exceptions=True)
                self.storage.end_snapshot_tracking(int(time.time()))

    async def _reconnecting_stream(self, rpc: SolanaRpc) -> None:
        delay = 1.0
        while True:
            try:
                await self._stream_once(rpc)
                delay = 1.0
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("WebSocket koptu; %.1f saniye sonra tekrar", delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.settings.reconnect_max_seconds)

    async def _stream_once(self, rpc: SolanaRpc) -> None:
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=self.settings.rpc_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(
                self.settings.solana_ws_url, heartbeat=20, autoping=True
            ) as ws:
                await ws.send_json({"jsonrpc": "2.0", "id": 1,
                                    "method": "slotSubscribe", "params": []})
                await ws.send_json({
                    "jsonrpc": "2.0", "id": 2, "method": "logsSubscribe",
                    "params": [
                        {"mentions": [self.settings.launch_program_id]},
                        {"commitment": self.settings.commitment},
                    ],
                })
                subscription_by_id: dict[int, str] = {}
                async for message in ws:
                    if message.type == aiohttp.WSMsgType.ERROR:
                        raise message.data
                    if message.type != aiohttp.WSMsgType.TEXT:
                        continue
                    body = json.loads(message.data)
                    if "id" in body and "result" in body:
                        subscription_by_id[int(body["result"])] = (
                            "slot" if body["id"] == 1 else "logs"
                        )
                        continue
                    params = body.get("params") or {}
                    kind = subscription_by_id.get(params.get("subscription"))
                    if kind == "slot":
                        await self._handle_slot(params)
                    elif kind == "logs":
                        await self._handle_logs(params, rpc)

    async def _handle_slot(self, params: dict[str, Any]) -> None:
        result = params.get("result") or {}
        slot = int(result.get("slot", result.get("parent", 0)))
        if slot <= 0:
            return
        gap = self.slot_tracker.observe(slot)
        self.storage.set_state("last_observed_slot", slot)
        if gap:
            start, end = gap
            record = SlotGap(start, end, utc_now_iso(), self.provider)
            self.storage.save_gap(record)
            if end - start + 1 <= self.settings.max_backfill_slots:
                await self._gap_queue.put(gap)
            else:
                self.storage.update_gap(start, end, "SKIPPED_TOO_LARGE", "limit asildi")

    async def _handle_logs(self, params: dict[str, Any], rpc: SolanaRpc,
                           defer_create: bool = True) -> None:
        received_at = str(params.get("_received_at") or utc_now_iso())
        started = float(params.get("_received_monotonic") or monotonic())
        result = params.get("result") or {}
        slot = int((result.get("context") or {}).get("slot", 0))
        value = result.get("value") or {}
        signature = value.get("signature")
        if not signature or slot <= 0:
            return
        logs = tuple(value.get("logs") or ())
        if value.get("err"):
            return
        is_create = is_pump_creation_logs(logs)
        if is_create and defer_create:
            try:
                queued = dict(params)
                queued["_received_at"] = received_at
                queued["_received_monotonic"] = started
                self._launch_queue.put_nowait(queued)
            except asyncio.QueueFull:
                logger.error("Launch RPC kuyrugu dolu; signature=%s", signature)
            return
        try:
            trades = decode_pump_trade_logs(logs)
        except PumpDecodeError:
            logger.exception("Pump TradeEvent decode edilemedi: %s", signature)
            trades = []
        scoped_trades = []
        for trade in trades:
            launch_timestamp = self._tracked_launches.get(trade.mint)
            trade_age = (
                trade.timestamp - launch_timestamp
                if launch_timestamp is not None else -1
            )
            if 0 <= trade_age <= self.settings.trade_track_seconds:
                scoped_trades.append(trade)
        if not is_create and not scoped_trades:
            return
        transaction = (
            await rpc.get_transaction(signature, self.settings.commitment)
            if is_create else None
        )
        if is_create and transaction is None:
            raise RpcError("getTransaction gecici olarak null dondu")
        processed_at = utc_now_iso()
        latency_ms = int((monotonic() - started) * 1000)
        event = ChainEvent(
            signature=signature, slot=slot,
            program_id=self.settings.launch_program_id or "",
            commitment=self.settings.commitment,
            provider_name=self.provider, client_received_at=received_at,
            processed_at=processed_at,
            block_time=(transaction or {}).get("blockTime")
            or (scoped_trades[0].timestamp if scoped_trades else None),
            ingestion_latency_ms=latency_ms,
            data_completeness="COMPLETE" if transaction else "LOG_EVENT",
            transaction_error=json.dumps(value.get("err")) if value.get("err") else None,
            logs=logs if transaction else tuple(
                line for line in logs if line.startswith("Program data: ")
            ),
            raw_transaction=transaction,
        )
        self.storage.save_event(event)
        if transaction:
            try:
                launch = decode_pump_launch(transaction)
            except PumpDecodeError:
                logger.exception("Pump create decode edilemedi: %s", signature)
            else:
                if launch is not None:
                    self._save_launch(launch, event, received_at, enable_tracking=True)
                    logger.info(
                        "launch slot=%s mint=%s symbol=%s latency_ms=%s",
                        slot, launch.mint, launch.symbol, latency_ms,
                    )
        # Create ve ilk buy ayni transaction'da olabilir; launch kaydindan sonra
        # o transaction'in trade eventlerini yeniden kapsam kontrolunden gecir.
        if is_create:
            scoped_trades = [
                trade for trade in trades
                if trade.mint in self._tracked_launches
                and 0 <= trade.timestamp - self._tracked_launches[trade.mint]
                <= self.settings.trade_track_seconds
            ]
        for trade in scoped_trades:
            if self.storage.save_trade(trade, signature, slot, received_at):
                launch_timestamp = self._tracked_launches.get(trade.mint)
                if (
                    self.settings.wallet_enrichment_enabled and trade.is_buy
                    and launch_timestamp is not None
                    and 0 <= trade.timestamp - launch_timestamp <= 10
                ):
                    self.storage.enqueue_early_buyer(
                        trade.user, trade.mint,
                        self.settings.wallet_early_buyer_limit, received_at,
                    )
                if (
                    self.settings.sniper_enabled and trade.is_buy
                    and launch_timestamp is not None
                    and 0 <= trade.timestamp - launch_timestamp
                    <= self.settings.sniper_max_trade_age_seconds
                ):
                    self.storage.enqueue_transaction_enrichment(
                        signature, trade.mint, trade.user, slot, trade.timestamp,
                        trade.timestamp - launch_timestamp,
                        self.settings.sniper_early_buyer_limit, received_at,
                    )
                logger.debug(
                    "trade slot=%s mint=%s side=%s user=%s",
                    slot, trade.mint, "BUY" if trade.is_buy else "SELL", trade.user,
                )

    async def _launch_transaction_worker(self, rpc: SolanaRpc) -> None:
        """HTTP RPC arizalarinin WebSocket okuma dongusunu kapatmasini engeller."""
        while True:
            params = await self._launch_queue.get()
            value = ((params.get("result") or {}).get("value") or {})
            signature = value.get("signature", "unknown")
            slot = int((params.get("result") or {}).get("context", {}).get("slot", 0))
            try:
                for attempt in range(1, 4):
                    try:
                        await self._handle_logs(params, rpc, defer_create=False)
                        break
                    except asyncio.CancelledError:
                        raise
                    except (aiohttp.ClientError, asyncio.TimeoutError, RpcError) as exc:
                        if attempt == 3:
                            logger.warning(
                                "Launch transaction alinamadi; signature=%s "
                                "deneme=%s hata=%s:%s",
                                signature, attempt, type(exc).__name__, str(exc),
                            )
                            if slot > 0:
                                await self._gap_queue.put((slot, slot))
                        else:
                            await asyncio.sleep(2 ** (attempt - 1))
                    except Exception:
                        logger.exception(
                            "Launch transaction worker beklenmeyen hata signature=%s",
                            signature,
                        )
                        break
            finally:
                self._launch_queue.task_done()

    async def _backfill_worker(self, rpc: SolanaRpc) -> None:
        while True:
            start, end = await self._gap_queue.get()
            try:
                blocks = await rpc.get_blocks(start, end, self.settings.commitment)
                matched = 0
                for slot in blocks:
                    block = await rpc.get_block(slot, self.settings.commitment)
                    matched += self._save_backfilled_block(slot, block or {})
                self.storage.update_gap(start, end, "BACKFILLED", f"events={matched}")
            except Exception as exc:
                logger.exception("Backfill basarisiz: %s-%s", start, end)
                self.storage.update_gap(start, end, "FAILED", str(exc)[:500])
            finally:
                self._gap_queue.task_done()

    async def _snapshot_worker(self) -> None:
        while True:
            try:
                created = await asyncio.to_thread(
                    self.storage.create_due_snapshots, int(time.time())
                )
                if created:
                    logger.info("snapshot olusturuldu: %s", created)
                scored = await asyncio.to_thread(
                    score_snapshots, self.storage, None, True
                )
                if scored:
                    logger.info("risk karari olusturuldu: %s", scored)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Snapshot worker hatasi")
            await asyncio.sleep(0.5)

    def _paper_assumptions(self) -> PaperAssumptions:
        return PaperAssumptions(
            notional_quote=self.settings.paper_notional_lamports,
            latency_seconds=self.settings.paper_latency_seconds,
            slippage_bps=self.settings.paper_slippage_bps,
            base_fee=self.settings.paper_base_fee_lamports,
            priority_fee=self.settings.paper_priority_fee_lamports,
            jito_tip=self.settings.paper_jito_tip_lamports,
            max_reserve_impact_bps=self.settings.paper_max_reserve_impact_bps,
            max_fill_wait_seconds=self.settings.paper_max_fill_wait_seconds,
        )

    async def _paper_worker(self) -> None:
        assumptions = self._paper_assumptions()
        while True:
            try:
                entries, outcomes, labels = await asyncio.to_thread(
                    run_paper_cycle, self.storage, assumptions, int(time.time()),
                    self.settings.trade_track_seconds, False, 25, 10, 120,
                )
                if entries or outcomes or labels:
                    logger.info(
                        "paper cycle entry=%s outcome=%s label=%s",
                        entries, outcomes, labels,
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Paper worker hatasi")
            await asyncio.sleep(5.0)

    async def _wallet_analysis_worker(self, rpc: SolanaRpc) -> None:
        """Slow, bounded enrichment path; never awaited by live log handling."""
        while True:
            item = await asyncio.to_thread(
                self.storage.claim_wallet_analysis, int(time.time())
            )
            if item is None:
                await asyncio.sleep(1.0)
                continue
            try:
                await self._analyze_wallet(rpc, dict(item))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                attempts = int(item["attempts"]) + 1
                retry_at = int(time.time()) + min(300, 2 ** min(attempts, 8))
                self.storage.fail_wallet_analysis(
                    int(item["id"]), str(exc), retry_at
                )
                logger.warning(
                    "wallet analizi ertelendi address=%s hata=%s",
                    item["address"], exc,
                )

    async def _sniper_enrichment_worker(self, rpc: SolanaRpc) -> None:
        while True:
            item = await asyncio.to_thread(
                self.storage.claim_transaction_enrichment, int(time.time())
            )
            if item is None:
                await asyncio.sleep(1.0)
                continue
            try:
                transaction = await rpc.get_transaction(
                    item["signature"], self.settings.commitment
                )
                if transaction is None:
                    raise RpcError("getTransaction henuz null")
                evidence = analyze_transaction(transaction)
                self.storage.save_transaction_evidence(
                    int(item["id"]), dict(item), {
                        "fee_payer": evidence.fee_payer,
                        "transaction_fee_lamports": evidence.transaction_fee_lamports,
                        "compute_units_consumed": evidence.compute_units_consumed,
                        "compute_unit_limit": evidence.compute_unit_limit,
                        "compute_unit_price_micro_lamports": (
                            evidence.compute_unit_price_micro_lamports
                        ),
                        "estimated_priority_fee_lamports": (
                            evidence.estimated_priority_fee_lamports
                        ),
                        "jito_tip_lamports": evidence.jito_tip_lamports,
                        "jito_tip_account": evidence.jito_tip_account,
                        "jitodontfront_present": evidence.jitodontfront_present,
                    },
                )
                await asyncio.to_thread(score_snipers, self.storage, item["mint"])
                await asyncio.to_thread(
                    score_snapshots, self.storage, item["mint"], False
                )
                await asyncio.sleep(self.settings.sniper_rpc_interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                attempts = int(item["attempts"]) + 1
                retry_at = int(time.time()) + min(300, 2 ** min(attempts, 8))
                self.storage.fail_transaction_enrichment(
                    int(item["id"]), str(exc), retry_at
                )
                logger.warning(
                    "sniper tx analizi ertelendi signature=%s hata=%s",
                    item["signature"], exc,
                )
                await asyncio.sleep(self.settings.sniper_rpc_interval_seconds)

    async def _analyze_wallet(
        self, rpc: SolanaRpc, item: dict[str, Any]
    ) -> None:
        address = str(item["address"])
        signatures: list[dict[str, Any]] = []
        before: str | None = None
        history_complete = False
        for _ in range(self.settings.wallet_max_signature_pages):
            page = await rpc.get_signatures_for_address(
                address, self.settings.commitment,
                self.settings.wallet_signature_page_size, before,
            )
            signatures.extend(page)
            await asyncio.sleep(self.settings.wallet_rpc_interval_seconds)
            if len(page) < self.settings.wallet_signature_page_size:
                history_complete = True
                break
            before = page[-1].get("signature") if page else None
            if not before:
                history_complete = True
                break

        usable = [row for row in signatures if not row.get("err")]
        oldest = usable[-1] if usable else (signatures[-1] if signatures else None)
        transfers: list[FundingTransfer] = []
        # En eski birkac islem fonlama hesabini bulmak icin yeterli bir baseline'dir.
        for row in reversed(usable[-5:]):
            signature = row.get("signature")
            if not signature:
                continue
            transaction = await rpc.get_transaction(
                signature, self.settings.commitment
            )
            await asyncio.sleep(self.settings.wallet_rpc_interval_seconds)
            if transaction:
                transfers.extend(inbound_system_transfers(
                    transaction, address, signature
                ))
            if transfers:
                break
        funding = max(transfers, key=lambda value: value.lamports) if transfers else None
        confidence = 0.9 if funding and history_complete else (0.55 if funding else 0.0)
        self.storage.save_wallet_analysis(
            int(item["id"]), address, len(signatures), history_complete,
            oldest.get("signature") if oldest else None,
            oldest.get("blockTime") if oldest else None,
            funding.source if funding else None,
            funding.signature if funding else None,
            funding.lamports if funding else None,
            funding.block_time if funding else None,
            ("FIRST_FUNDING" if history_complete else "RECENT_FUNDING_CANDIDATE")
            if funding else None,
            confidence,
        )
        await asyncio.to_thread(score_snapshots, self.storage, item["mint"], False)
        if self.settings.sniper_enabled:
            await asyncio.to_thread(score_snipers, self.storage, item["mint"])
        logger.info(
            "wallet analiz edildi address=%s signatures=%s complete=%s funder=%s",
            address, len(signatures), history_complete,
            funding.source if funding else "yok",
        )

    def _save_backfilled_block(self, slot: int, block: dict[str, Any]) -> int:
        count = 0
        for index, item in enumerate(block.get("transactions") or []):
            tx = item.get("transaction") or {}
            signatures = tx.get("signatures") or []
            merged = {"transaction": tx, "meta": item.get("meta")}
            if not signatures or not transaction_mentions_program(
                merged, self.settings.launch_program_id or ""
            ):
                continue
            logs = tuple((item.get("meta") or {}).get("logMessages") or ())
            try:
                launch = decode_pump_launch(merged)
                trades = decode_pump_trade_logs(logs)
            except PumpDecodeError:
                logger.exception("Backfill Pump event decode edilemedi: slot=%s", slot)
                continue
            if launch is None and not trades:
                continue
            now = utc_now_iso()
            event = ChainEvent(
                signature=signatures[0], slot=slot,
                program_id=self.settings.launch_program_id or "",
                commitment=self.settings.commitment, provider_name=self.provider,
                client_received_at=now, processed_at=now,
                block_time=block.get("blockTime"), tx_index_in_block=index,
                is_backfilled=True, stream_gap_detected=True,
                data_completeness="BACKFILLED", raw_transaction=merged,
            )
            if self.storage.save_event(event):
                count += 1
            if launch is not None:
                self._save_launch(launch, event, now, enable_tracking=False)
            for trade in trades:
                launch_timestamp = self._tracked_launches.get(trade.mint)
                if launch_timestamp is not None and (
                    0 <= trade.timestamp - launch_timestamp
                    <= self.settings.trade_track_seconds
                ):
                    self.storage.save_trade(trade, event.signature, slot, now)
        return count

    def _save_launch(
        self, launch: PumpLaunch, event: ChainEvent, first_seen_at: str,
        enable_tracking: bool,
    ) -> None:
        self.storage.save_token(TokenObservation(
            mint=launch.mint, creator=launch.creator, program_id=event.program_id,
            launch_slot=event.slot, block_time=event.block_time,
            first_signature=event.signature, first_seen_at=first_seen_at,
            data_completeness=event.data_completeness,
        ))
        self.storage.save_pump_launch(
            launch, event.signature, event.slot, event.block_time, first_seen_at
        )
        if enable_tracking:
            self.storage.enable_snapshot_tracking(
                launch.mint, launch.timestamp, first_seen_at
            )
            self._tracked_launches[launch.mint] = launch.timestamp
            if self.settings.wallet_enrichment_enabled:
                self.storage.enqueue_wallet(
                    launch.creator, launch.mint, "CREATOR", 100, first_seen_at
                )
