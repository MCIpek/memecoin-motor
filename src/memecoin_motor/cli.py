from __future__ import annotations

import argparse
import asyncio
import logging
import json
import sys
import time

from .config import Settings
from .service import CollectorService
from .storage import Storage
from .models import TokenObservation
from .pump_decoder import PumpDecodeError, decode_pump_launch
from .scoring import score_snapshots
from .paper import PaperAssumptions
from .paper_engine import run_paper_cycle
from .calibration import calibrate_x_bands


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="memecoin-motor")
    parser.add_argument("--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="SQLite semasini olustur")
    sub.add_parser("status", help="Yerel kayit sayilarini goster")
    sub.add_parser("doctor", help="Yapilandirmayi dogrula")
    sub.add_parser("redecode", help="Kayitli ham olaylari guncel IDL ile tekrar decode et")
    sub.add_parser("collect", help="Salt-okunur Solana collector'u baslat")
    snapshots = sub.add_parser("snapshots", help="Son snapshotlari goster")
    snapshots.add_argument("--limit", type=int, default=20)
    wallets = sub.add_parser("wallets", help="Token icin ilk/aktif cuzdanlari goster")
    wallets.add_argument("mint")
    wallets.add_argument("--limit", type=int, default=20)
    wallet = sub.add_parser("wallet", help="Derin cuzdan profilini goster")
    wallet.add_argument("address")
    creators = sub.add_parser("creators", help="Son creator gecmislerini goster")
    creators.add_argument("--limit", type=int, default=20)
    creator = sub.add_parser("creator", help="Bir creator yerel gecmisini goster")
    creator.add_argument("address")
    scoring = sub.add_parser("score", help="Risk baseline kararlarini hesapla")
    scoring.add_argument("--mint")
    scores = sub.add_parser("scores", help="Son risk kararlarini goster")
    scores.add_argument("--limit", type=int, default=20)
    sub.add_parser("paper-run", help="Cuzdansiz paper cycle calistir")
    papers = sub.add_parser("paper", help="Son sanal pozisyonlari goster")
    papers.add_argument("--limit", type=int, default=20)
    outcomes = sub.add_parser("outcomes", help="Paper sonuc etiketlerini goster")
    outcomes.add_argument("--limit", type=int, default=20)
    labels = sub.add_parser("labels", help="Tum kararlarin piyasa etiketlerini goster")
    labels.add_argument("--limit", type=int, default=20)
    v2 = sub.add_parser("outcomes-v2", help="Rezerv bazli yurutulebilir sonuclari goster")
    v2.add_argument("--limit", type=int, default=20)
    calibration = sub.add_parser("calibrate-x", help="Gercek dagilimlardan X bantlarini kalibre et")
    calibration.add_argument("--horizon", type=int, default=300)
    calibration.add_argument("--minimum-samples", type=int, default=30)
    bands = sub.add_parser("x-bands", help="Kalibre X bantlarini goster")
    bands.add_argument("--horizon", type=int, default=300)
    bands.add_argument("--limit", type=int, default=30)
    missed = sub.add_parser("missed-watchlist", help="Basarili IZLE kararlarini incele")
    missed.add_argument("--horizon", type=int, default=300)
    missed.add_argument("--minimum-x", type=float, default=1.5)
    missed.add_argument("--limit", type=int, default=30)
    sniper = sub.add_parser("sniper", help="Tokenin erken sniper skorlarini goster")
    sniper.add_argument("mint")
    sniper.add_argument("--limit", type=int, default=20)
    snipers = sub.add_parser("snipers", help="En yuksek sniper skorlarini goster")
    snipers.add_argument("--limit", type=int, default=50)
    sub.add_parser("sniper-backfill", help="Yerel trade'lerden tekrar erken giris say")
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = Settings.from_env()

    if args.command == "doctor":
        print(f"HTTP RPC : {settings.solana_http_url}")
        print(f"WebSocket: {settings.solana_ws_url}")
        print(f"Program  : {settings.launch_program_id or 'EKSIK'}")
        print(f"Database : {settings.database_path}")
        print(
            "Wallet AI: " + ("acik" if settings.wallet_enrichment_enabled else "kapali")
            + f"; ilk alici={settings.wallet_early_buyer_limit}; "
            + f"sayfa={settings.wallet_max_signature_pages}x"
            + f"{settings.wallet_signature_page_size}; "
            + f"RPC araligi={settings.wallet_rpc_interval_seconds:.1f}s"
        )
        print(
            f"Paper    : {'acik' if settings.paper_enabled else 'kapali'}; "
            f"notional={settings.paper_notional_lamports / 1_000_000_000:.3f} SOL; "
            f"latency={settings.paper_latency_seconds}s; "
            f"slippage={settings.paper_slippage_bps / 100:.2f}%"
            f"; fill penceresi={settings.paper_max_fill_wait_seconds}s"
        )
        print(
            f"Sniper   : {'acik' if settings.sniper_enabled else 'kapali'}; "
            f"ilk alici={settings.sniper_early_buyer_limit}; "
            f"yas<={settings.sniper_max_trade_age_seconds}s; "
            f"RPC araligi={settings.sniper_rpc_interval_seconds:.1f}s"
        )
        if not settings.launch_program_id:
            raise SystemExit("LAUNCH_PROGRAM_ID .env icinde ayarlanmali")
        print("Yapilandirma hazir.")
        return

    storage = Storage(settings.database_path)
    storage.initialize()
    try:
        if args.command == "init-db":
            print(f"Veritabani hazir: {settings.database_path}")
        elif args.command == "status":
            for name, count in storage.counts().items():
                print(f"{name}: {count}")
        elif args.command == "snapshots":
            for row in storage.recent_snapshots(max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "wallets":
            for row in storage.top_wallets(args.mint, max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "wallet":
            row = storage.wallet_profile(args.address)
            print(json.dumps(dict(row), ensure_ascii=False) if row else "Analiz yok/kuyrukta.")
        elif args.command == "creators":
            for row in storage.recent_creator_histories(max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "creator":
            row = storage.creator_history(args.address)
            print(json.dumps(dict(row), ensure_ascii=False) if row else "Creator bulunamadi.")
        elif args.command == "score":
            count = score_snapshots(storage, args.mint, False)
            print(f"Hesaplanan risk karari: {count}")
        elif args.command == "scores":
            for row in storage.recent_risk_decisions(max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "paper-run":
            assumptions = PaperAssumptions(
                settings.paper_notional_lamports,
                settings.paper_latency_seconds,
                settings.paper_slippage_bps,
                settings.paper_base_fee_lamports,
                settings.paper_priority_fee_lamports,
                settings.paper_jito_tip_lamports,
                settings.paper_max_reserve_impact_bps,
                settings.paper_max_fill_wait_seconds,
            )
            entries, outcomes, labels = run_paper_cycle(
                storage, assumptions, int(time.time()),
                settings.trade_track_seconds, recompute_outcomes=True,
            )
            print(
                f"Paper entry: {entries}; paper sonucu: {outcomes}; "
                f"piyasa etiketi: {labels}"
            )
        elif args.command == "paper":
            for row in storage.recent_paper_positions(max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "outcomes":
            for row in storage.recent_paper_outcomes(max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "labels":
            for row in storage.recent_market_outcomes(max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "outcomes-v2":
            for row in storage.recent_v2_outcomes(max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "calibrate-x":
            count = calibrate_x_bands(storage, args.horizon, args.minimum_samples)
            print(f"Kalibre edilen X bandi: {count}")
        elif args.command == "x-bands":
            for row in storage.calibrations(args.horizon, max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "missed-watchlist":
            for row in storage.missed_watchlist(args.horizon, args.minimum_x, max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "sniper":
            for row in storage.sniper_scores(args.mint, max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "snipers":
            for row in storage.sniper_scores(None, max(1, args.limit)):
                print(json.dumps(dict(row), ensure_ascii=False))
        elif args.command == "sniper-backfill":
            print(
                "Cuzdan davranis kaydi: "
                f"{storage.rebuild_wallet_behavior_stats()}"
            )
        elif args.command == "redecode":
            decoded = 0
            failed = 0
            for row in storage.raw_events():
                try:
                    launch = decode_pump_launch(json.loads(row["raw_transaction_json"]))
                except PumpDecodeError as exc:
                    failed += 1
                    logging.warning("%s decode edilemedi: %s", row["signature"], exc)
                    continue
                if launch is None:
                    continue
                storage.save_token(TokenObservation(
                    launch.mint, launch.creator, row["program_id"], row["slot"],
                    row["block_time"], row["signature"], row["client_received_at"],
                    row["data_completeness"],
                ))
                storage.save_pump_launch(
                    launch, row["signature"], row["slot"], row["block_time"],
                    row["client_received_at"],
                )
                decoded += 1
            removed = storage.reconcile_pump_tokens(settings.launch_program_id or "")
            removed_trades = storage.reconcile_trade_scope(settings.trade_track_seconds)
            print(
                f"Decode edilen launch: {decoded}; hatali create: {failed}; "
                f"dogrulanmamis minimal mint silindi: {removed}; "
                f"kapsam disi trade silindi: {removed_trades}"
            )
        elif args.command == "collect":
            asyncio.run(CollectorService(settings, storage).run())
    except KeyboardInterrupt:
        print("Collector durduruldu.")
    finally:
        storage.close()


if __name__ == "__main__":
    main()
