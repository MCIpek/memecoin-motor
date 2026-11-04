from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import ChainEvent, SlotGap, TokenObservation
from .pump_decoder import PumpLaunch, PumpTrade


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS chain_events (
 signature TEXT PRIMARY KEY, slot INTEGER NOT NULL, program_id TEXT NOT NULL,
 block_time INTEGER, tx_index_in_block INTEGER, commitment TEXT NOT NULL,
 provider_name TEXT NOT NULL, client_received_at TEXT NOT NULL,
 processed_at TEXT NOT NULL, ingestion_latency_ms INTEGER,
 is_backfilled INTEGER NOT NULL, stream_gap_detected INTEGER NOT NULL,
 data_completeness TEXT NOT NULL, transaction_error TEXT,
 logs_json TEXT NOT NULL, raw_transaction_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_chain_events_slot ON chain_events(slot);
CREATE TABLE IF NOT EXISTS tokens_minimal (
 mint TEXT PRIMARY KEY, creator TEXT, program_id TEXT NOT NULL,
 launch_slot INTEGER NOT NULL, block_time INTEGER,
 first_signature TEXT NOT NULL, first_seen_at TEXT NOT NULL,
 data_completeness TEXT NOT NULL, promoted INTEGER NOT NULL DEFAULT 0,
 rejection_reason TEXT,
 FOREIGN KEY(first_signature) REFERENCES chain_events(signature)
);
CREATE INDEX IF NOT EXISTS idx_tokens_launch_slot ON tokens_minimal(launch_slot);
CREATE TABLE IF NOT EXISTS pump_launches (
 mint TEXT PRIMARY KEY,
 signature TEXT NOT NULL UNIQUE,
 slot INTEGER NOT NULL,
 block_time INTEGER,
 first_seen_at TEXT NOT NULL,
 instruction_name TEXT NOT NULL,
 name TEXT NOT NULL,
 symbol TEXT NOT NULL,
 uri TEXT NOT NULL,
 bonding_curve TEXT NOT NULL,
 user_address TEXT NOT NULL,
 creator TEXT NOT NULL,
 event_timestamp INTEGER NOT NULL,
 virtual_token_reserves INTEGER NOT NULL,
 virtual_sol_reserves INTEGER NOT NULL,
 real_token_reserves INTEGER NOT NULL,
 token_total_supply INTEGER NOT NULL,
 token_program TEXT NOT NULL,
 is_mayhem_mode INTEGER NOT NULL,
 is_cashback_enabled INTEGER NOT NULL,
 quote_mint TEXT NOT NULL,
 quote_asset TEXT NOT NULL,
 virtual_quote_reserves INTEGER NOT NULL,
 FOREIGN KEY(signature) REFERENCES chain_events(signature)
);
CREATE INDEX IF NOT EXISTS idx_pump_launches_slot ON pump_launches(slot);
CREATE TABLE IF NOT EXISTS snapshot_tracking (
 mint TEXT PRIMARY KEY,
 launch_timestamp INTEGER NOT NULL,
 enabled_at TEXT NOT NULL,
 ended_at INTEGER,
 FOREIGN KEY(mint) REFERENCES pump_launches(mint)
);
CREATE TABLE IF NOT EXISTS pump_trades (
 signature TEXT NOT NULL,
 event_index INTEGER NOT NULL,
 slot INTEGER NOT NULL,
 observed_at TEXT NOT NULL,
 mint TEXT NOT NULL,
 is_buy INTEGER NOT NULL,
 user_address TEXT NOT NULL,
 event_timestamp INTEGER NOT NULL,
 token_amount INTEGER NOT NULL,
 quote_amount INTEGER NOT NULL,
 quote_asset TEXT NOT NULL,
 sol_amount INTEGER NOT NULL,
 virtual_sol_reserves INTEGER NOT NULL,
 virtual_token_reserves INTEGER NOT NULL,
 real_sol_reserves INTEGER NOT NULL,
 real_token_reserves INTEGER NOT NULL,
 virtual_quote_reserves INTEGER NOT NULL,
 real_quote_reserves INTEGER NOT NULL,
 fee INTEGER NOT NULL,
 creator TEXT NOT NULL,
 ix_name TEXT NOT NULL,
 raw_event_json TEXT NOT NULL,
 PRIMARY KEY(signature,event_index),
 FOREIGN KEY(signature) REFERENCES chain_events(signature)
);
CREATE INDEX IF NOT EXISTS idx_pump_trades_mint_time
ON pump_trades(mint,event_timestamp,slot,event_index);
CREATE INDEX IF NOT EXISTS idx_pump_trades_user ON pump_trades(user_address);

CREATE TABLE IF NOT EXISTS wallet_positions (
 mint TEXT NOT NULL,
 user_address TEXT NOT NULL,
 buy_token_amount INTEGER NOT NULL DEFAULT 0,
 sell_token_amount INTEGER NOT NULL DEFAULT 0,
 buy_quote_amount INTEGER NOT NULL DEFAULT 0,
 sell_quote_amount INTEGER NOT NULL DEFAULT 0,
 buy_count INTEGER NOT NULL DEFAULT 0,
 sell_count INTEGER NOT NULL DEFAULT 0,
 first_trade_timestamp INTEGER NOT NULL,
 last_trade_timestamp INTEGER NOT NULL,
 PRIMARY KEY(mint,user_address)
);
CREATE TABLE IF NOT EXISTS wallet_behavior_stats (
 address TEXT PRIMARY KEY,
 early_launch_count INTEGER NOT NULL DEFAULT 0,
 updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS token_snapshots (
 mint TEXT NOT NULL,
 target_age_seconds INTEGER NOT NULL,
 cutoff_timestamp INTEGER NOT NULL,
 generated_at TEXT NOT NULL,
 generation_delay_ms INTEGER NOT NULL,
 trade_count INTEGER NOT NULL,
 unique_buyers INTEGER NOT NULL,
 unique_sellers INTEGER NOT NULL,
 buy_quote_amount INTEGER NOT NULL,
 sell_quote_amount INTEGER NOT NULL,
 net_quote_flow INTEGER NOT NULL,
 buy_token_amount INTEGER NOT NULL,
 sell_token_amount INTEGER NOT NULL,
 top_buyer_share REAL NOT NULL,
 top5_buyer_share REAL NOT NULL,
 creator_sold INTEGER NOT NULL,
 latest_virtual_quote_reserves INTEGER NOT NULL,
 latest_virtual_token_reserves INTEGER NOT NULL,
 price_quote_per_token REAL,
 snapshot_quality TEXT NOT NULL,
 PRIMARY KEY(mint,target_age_seconds)
);
CREATE TABLE IF NOT EXISTS stream_gaps (
 id INTEGER PRIMARY KEY AUTOINCREMENT, start_slot INTEGER NOT NULL,
 end_slot INTEGER NOT NULL, detected_at TEXT NOT NULL,
 provider_name TEXT NOT NULL, status TEXT NOT NULL, detail TEXT,
 UNIQUE(start_slot, end_slot, provider_name)
);
CREATE TABLE IF NOT EXISTS service_state (
 key TEXT PRIMARY KEY, value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS wallet_analysis_queue (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 address TEXT NOT NULL,
 mint TEXT NOT NULL,
 reason TEXT NOT NULL,
 priority INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'PENDING',
 attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt_at INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 last_error TEXT,
 UNIQUE(address,mint,reason)
);
CREATE INDEX IF NOT EXISTS idx_wallet_queue_work
ON wallet_analysis_queue(status,next_attempt_at,priority,id);
CREATE INDEX IF NOT EXISTS idx_wallet_queue_address_mint
ON wallet_analysis_queue(address,mint);
CREATE TABLE IF NOT EXISTS wallet_profiles (
 address TEXT PRIMARY KEY,
 analyzed_at TEXT NOT NULL,
 signatures_scanned INTEGER NOT NULL,
 history_complete INTEGER NOT NULL,
 oldest_scanned_signature TEXT,
 oldest_scanned_block_time INTEGER,
 likely_funder TEXT,
 funding_signature TEXT,
 funding_lamports INTEGER,
 funding_block_time INTEGER,
 funding_label TEXT,
 confidence REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wallet_profiles_funder
ON wallet_profiles(likely_funder);
CREATE TABLE IF NOT EXISTS wallet_edges (
 source_address TEXT NOT NULL,
 target_address TEXT NOT NULL,
 edge_type TEXT NOT NULL,
 signature TEXT NOT NULL,
 block_time INTEGER,
 lamports INTEGER NOT NULL,
 confidence REAL NOT NULL,
 PRIMARY KEY(source_address,target_address,edge_type,signature)
);
CREATE TABLE IF NOT EXISTS risk_decisions (
 mint TEXT NOT NULL,
 snapshot_age_seconds INTEGER NOT NULL,
 evaluated_at TEXT NOT NULL,
 ruleset_version TEXT NOT NULL,
 decision TEXT NOT NULL,
 risk_score INTEGER NOT NULL,
 opportunity_score INTEGER NOT NULL,
 confidence REAL NOT NULL,
 reasons_json TEXT NOT NULL,
 warnings_json TEXT NOT NULL,
 features_json TEXT NOT NULL,
 PRIMARY KEY(mint,snapshot_age_seconds)
);
CREATE TABLE IF NOT EXISTS paper_positions (
 mint TEXT NOT NULL,
 decision_age_seconds INTEGER NOT NULL,
 created_at TEXT NOT NULL,
 status TEXT NOT NULL,
 failure_reason TEXT,
 decision_cutoff_timestamp INTEGER NOT NULL,
 entry_signature TEXT,
 entry_event_index INTEGER,
 entry_timestamp INTEGER,
 entry_slot INTEGER,
 notional_quote INTEGER NOT NULL,
 quote_asset TEXT NOT NULL,
 entry_price_quote_per_raw_token REAL,
 token_quantity_raw REAL,
 entry_fee INTEGER NOT NULL,
 estimated_impact_bps INTEGER,
 assumptions_json TEXT NOT NULL,
 PRIMARY KEY(mint,decision_age_seconds)
);
CREATE TABLE IF NOT EXISTS paper_outcomes (
 mint TEXT NOT NULL,
 decision_age_seconds INTEGER NOT NULL,
 horizon_seconds INTEGER NOT NULL,
 evaluated_at TEXT NOT NULL,
 sample_count INTEGER NOT NULL,
 max_x REAL NOT NULL,
 min_x REAL NOT NULL,
 final_x REAL NOT NULL,
 max_drawdown_pct REAL NOT NULL,
 hit_1_5x INTEGER NOT NULL,
 hit_2x INTEGER NOT NULL,
 hit_3x INTEGER NOT NULL,
 hit_5x INTEGER NOT NULL,
 data_quality TEXT NOT NULL,
 PRIMARY KEY(mint,decision_age_seconds,horizon_seconds)
);
CREATE TABLE IF NOT EXISTS market_outcomes (
 mint TEXT NOT NULL,
 decision_age_seconds INTEGER NOT NULL,
 horizon_seconds INTEGER NOT NULL,
 evaluated_at TEXT NOT NULL,
 reference_signature TEXT NOT NULL,
 reference_timestamp INTEGER NOT NULL,
 sample_count INTEGER NOT NULL,
 max_market_x REAL NOT NULL,
 min_market_x REAL NOT NULL,
 final_market_x REAL NOT NULL,
 hit_1_5x INTEGER NOT NULL,
 hit_2x INTEGER NOT NULL,
 hit_3x INTEGER NOT NULL,
 hit_5x INTEGER NOT NULL,
 data_quality TEXT NOT NULL,
 PRIMARY KEY(mint,decision_age_seconds,horizon_seconds)
);
CREATE TABLE IF NOT EXISTS transaction_enrichment_queue (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 signature TEXT NOT NULL UNIQUE,
 mint TEXT NOT NULL,
 user_address TEXT NOT NULL,
 slot INTEGER NOT NULL,
 event_timestamp INTEGER NOT NULL,
 trade_age_seconds INTEGER NOT NULL,
 priority INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'PENDING',
 attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt_at INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_tx_enrichment_work
ON transaction_enrichment_queue(status,next_attempt_at,priority,id);
CREATE TABLE IF NOT EXISTS early_trade_metadata (
 signature TEXT PRIMARY KEY,
 mint TEXT NOT NULL,
 user_address TEXT NOT NULL,
 slot INTEGER NOT NULL,
 event_timestamp INTEGER NOT NULL,
 trade_age_seconds INTEGER NOT NULL,
 analyzed_at TEXT NOT NULL,
 fee_payer TEXT,
 transaction_fee_lamports INTEGER,
 compute_units_consumed INTEGER,
 compute_unit_limit INTEGER,
 compute_unit_price_micro_lamports INTEGER,
 estimated_priority_fee_lamports INTEGER,
 jito_tip_lamports INTEGER NOT NULL DEFAULT 0,
 jito_tip_account TEXT,
 jitodontfront_present INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_early_trade_meta_mint_slot
ON early_trade_metadata(mint,slot);
CREATE INDEX IF NOT EXISTS idx_early_trade_meta_mint_user
ON early_trade_metadata(mint,user_address);
CREATE INDEX IF NOT EXISTS idx_early_trade_meta_fee_payer
ON early_trade_metadata(mint,slot,fee_payer);
CREATE TABLE IF NOT EXISTS sniper_scores (
 mint TEXT NOT NULL,
 user_address TEXT NOT NULL,
 calculated_at TEXT NOT NULL,
 score INTEGER NOT NULL,
 classification TEXT NOT NULL,
 confidence REAL NOT NULL,
 first_buy_age_seconds INTEGER NOT NULL,
 same_slot_early_buyers INTEGER NOT NULL,
 repeated_early_launches INTEGER NOT NULL,
 quick_sell_seconds INTEGER,
 same_funder_peers INTEGER NOT NULL,
 same_fee_payer_peers INTEGER NOT NULL,
 jito_routed INTEGER NOT NULL,
 jito_tip_lamports INTEGER NOT NULL,
 priority_fee_lamports INTEGER,
 bundle_likelihood TEXT NOT NULL,
 reasons_json TEXT NOT NULL,
 PRIMARY KEY(mint,user_address)
);
CREATE TABLE IF NOT EXISTS paper_v2_positions (
 mint TEXT NOT NULL, decision_age_seconds INTEGER NOT NULL,
 experiment_group TEXT NOT NULL, is_canonical INTEGER NOT NULL,
 engine_version TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL,
 failure_reason TEXT, decision_cutoff_timestamp INTEGER NOT NULL,
 fill_deadline_timestamp INTEGER NOT NULL, entry_signature TEXT,
 entry_timestamp INTEGER, entry_slot INTEGER, notional_quote INTEGER NOT NULL,
 quote_asset TEXT NOT NULL, entry_price REAL, token_quantity REAL,
 entry_fee INTEGER NOT NULL, protocol_fee_bps INTEGER,
 estimated_impact_bps INTEGER, entry_quote_reserve INTEGER,
 entry_token_reserve INTEGER, assumptions_json TEXT NOT NULL,
 PRIMARY KEY(mint,decision_age_seconds)
);
CREATE INDEX IF NOT EXISTS idx_paper_v2_canonical
ON paper_v2_positions(is_canonical,status,entry_timestamp);
CREATE TABLE IF NOT EXISTS executable_outcomes_v2 (
 mint TEXT NOT NULL, decision_age_seconds INTEGER NOT NULL,
 horizon_seconds INTEGER NOT NULL, decision TEXT NOT NULL,
 is_canonical INTEGER NOT NULL, evaluated_at TEXT NOT NULL,
 sample_count INTEGER NOT NULL, max_x REAL NOT NULL, min_x REAL NOT NULL,
 final_x REAL NOT NULL, strategy_x REAL NOT NULL, exit_reason TEXT NOT NULL,
 max_drawdown_pct REAL NOT NULL, hit_1_5x INTEGER NOT NULL,
 hit_2x INTEGER NOT NULL, hit_3x INTEGER NOT NULL, hit_5x INTEGER NOT NULL,
 data_quality TEXT NOT NULL, tranches_json TEXT NOT NULL,
 PRIMARY KEY(mint,decision_age_seconds,horizon_seconds)
);
CREATE TABLE IF NOT EXISTS x_band_calibration (
 horizon_seconds INTEGER NOT NULL, age_seconds INTEGER NOT NULL,
 decision TEXT NOT NULL, risk_bucket INTEGER NOT NULL,
 opportunity_bucket INTEGER NOT NULL, sample_count INTEGER NOT NULL,
 p25_x REAL NOT NULL, p50_x REAL NOT NULL, p75_x REAL NOT NULL,
 p90_x REAL NOT NULL, hit_1_5_rate REAL NOT NULL, hit_2_rate REAL NOT NULL,
 hit_3_rate REAL NOT NULL, hit_5_rate REAL NOT NULL,
 final_profit_rate REAL NOT NULL, calibrated_at TEXT NOT NULL,
 PRIMARY KEY(horizon_seconds,age_seconds,decision,risk_bucket,opportunity_bucket)
);
"""


class Storage:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row

    def initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(SCHEMA)
            columns = {
                row["name"] for row in self._connection.execute(
                    "PRAGMA table_info(snapshot_tracking)"
                ).fetchall()
            }
            if "ended_at" not in columns:
                self._connection.execute(
                    "ALTER TABLE snapshot_tracking ADD COLUMN ended_at INTEGER"
                )
            self._connection.execute(
                "UPDATE wallet_analysis_queue SET status='PENDING' WHERE status='RUNNING'"
            )
            self._connection.execute(
                """UPDATE transaction_enrichment_queue SET status='PENDING'
                WHERE status='RUNNING'"""
            )
            self._connection.execute(
                """UPDATE paper_positions SET status='SKIPPED',
                failure_reason='INCOMPLETE_TRACKING'
                WHERE status='FAILED' AND failure_reason='NO_LATER_TRADE'
                AND EXISTS (SELECT 1 FROM snapshot_tracking st
                 JOIN pump_launches l ON l.mint=st.mint
                 WHERE st.mint=paper_positions.mint AND st.ended_at IS NOT NULL
                 AND st.ended_at<l.event_timestamp+600)"""
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def save_event(self, event: ChainEvent) -> bool:
        values = (
            event.signature, event.slot, event.program_id, event.block_time,
            event.tx_index_in_block, event.commitment, event.provider_name,
            event.client_received_at, event.processed_at,
            event.ingestion_latency_ms, int(event.is_backfilled),
            int(event.stream_gap_detected), event.data_completeness,
            event.transaction_error, json.dumps(event.logs, ensure_ascii=False),
            json.dumps(event.raw_transaction, ensure_ascii=False)
            if event.raw_transaction is not None else None,
        )
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """INSERT OR IGNORE INTO chain_events (
                signature, slot, program_id, block_time, tx_index_in_block,
                commitment, provider_name, client_received_at, processed_at,
                ingestion_latency_ms, is_backfilled, stream_gap_detected,
                data_completeness, transaction_error, logs_json,
                raw_transaction_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                values,
            )
            return cursor.rowcount == 1

    def save_token(self, token: TokenObservation) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """INSERT OR IGNORE INTO tokens_minimal (
                mint, creator, program_id, launch_slot, block_time,
                first_signature, first_seen_at, data_completeness)
                VALUES (?,?,?,?,?,?,?,?)""",
                (token.mint, token.creator, token.program_id, token.launch_slot,
                 token.block_time, token.first_signature, token.first_seen_at,
                 token.data_completeness),
            )
            return cursor.rowcount == 1

    def save_pump_launch(
        self,
        launch: PumpLaunch,
        signature: str,
        slot: int,
        block_time: int | None,
        first_seen_at: str,
    ) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """INSERT OR IGNORE INTO pump_launches (
                mint,signature,slot,block_time,first_seen_at,instruction_name,
                name,symbol,uri,bonding_curve,user_address,creator,event_timestamp,
                virtual_token_reserves,virtual_sol_reserves,real_token_reserves,
                token_total_supply,token_program,is_mayhem_mode,is_cashback_enabled,
                quote_mint,quote_asset,virtual_quote_reserves)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (launch.mint, signature, slot, block_time, first_seen_at,
                 launch.instruction_name, launch.name, launch.symbol, launch.uri,
                 launch.bonding_curve, launch.user, launch.creator, launch.timestamp,
                 launch.virtual_token_reserves, launch.virtual_sol_reserves,
                 launch.real_token_reserves, launch.token_total_supply,
                 launch.token_program, int(launch.is_mayhem_mode),
                 int(launch.is_cashback_enabled), launch.quote_mint,
                 launch.quote_asset, launch.virtual_quote_reserves),
            )
            return cursor.rowcount == 1

    def save_trade(
        self, trade: PumpTrade, signature: str, slot: int, observed_at: str
    ) -> bool:
        raw = json.dumps(asdict(trade), ensure_ascii=False)
        quote_amount = trade.effective_quote_amount
        with self._lock, self._connection:
            prior_buy = self._connection.execute(
                """SELECT 1 FROM pump_trades WHERE mint=? AND user_address=?
                AND is_buy=1 LIMIT 1""", (trade.mint, trade.user)
            ).fetchone()
            cursor = self._connection.execute(
                """INSERT OR IGNORE INTO pump_trades (
                signature,event_index,slot,observed_at,mint,is_buy,user_address,
                event_timestamp,token_amount,quote_amount,quote_asset,sol_amount,
                virtual_sol_reserves,virtual_token_reserves,real_sol_reserves,
                real_token_reserves,virtual_quote_reserves,real_quote_reserves,
                fee,creator,ix_name,raw_event_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (signature, trade.event_index, slot, observed_at, trade.mint,
                 int(trade.is_buy), trade.user, trade.timestamp,
                 trade.token_amount, quote_amount, trade.quote_asset,
                 trade.sol_amount, trade.virtual_sol_reserves,
                 trade.virtual_token_reserves, trade.real_sol_reserves,
                 trade.real_token_reserves, trade.virtual_quote_reserves,
                 trade.real_quote_reserves, trade.fee, trade.creator,
                 trade.ix_name, raw),
            )
            if cursor.rowcount != 1:
                return False
            if trade.is_buy and prior_buy is None:
                launch = self._connection.execute(
                    "SELECT event_timestamp FROM pump_launches WHERE mint=?",
                    (trade.mint,),
                ).fetchone()
                if launch and 0 <= trade.timestamp - int(launch["event_timestamp"]) <= 10:
                    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
                    self._connection.execute(
                        """INSERT INTO wallet_behavior_stats
                        (address,early_launch_count,updated_at) VALUES (?,1,?)
                        ON CONFLICT(address) DO UPDATE SET
                        early_launch_count=early_launch_count+1,
                        updated_at=excluded.updated_at""", (trade.user, now)
                    )
            buy_token = trade.token_amount if trade.is_buy else 0
            sell_token = 0 if trade.is_buy else trade.token_amount
            buy_quote = quote_amount if trade.is_buy else 0
            sell_quote = 0 if trade.is_buy else quote_amount
            self._connection.execute(
                """INSERT INTO wallet_positions (
                mint,user_address,buy_token_amount,sell_token_amount,
                buy_quote_amount,sell_quote_amount,buy_count,sell_count,
                first_trade_timestamp,last_trade_timestamp)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(mint,user_address) DO UPDATE SET
                buy_token_amount=buy_token_amount+excluded.buy_token_amount,
                sell_token_amount=sell_token_amount+excluded.sell_token_amount,
                buy_quote_amount=buy_quote_amount+excluded.buy_quote_amount,
                sell_quote_amount=sell_quote_amount+excluded.sell_quote_amount,
                buy_count=buy_count+excluded.buy_count,
                sell_count=sell_count+excluded.sell_count,
                first_trade_timestamp=MIN(first_trade_timestamp,excluded.first_trade_timestamp),
                last_trade_timestamp=MAX(last_trade_timestamp,excluded.last_trade_timestamp)""",
                (trade.mint, trade.user, buy_token, sell_token, buy_quote,
                 sell_quote, int(trade.is_buy), int(not trade.is_buy),
                 trade.timestamp, trade.timestamp),
            )
            return True

    def enable_snapshot_tracking(
        self, mint: str, launch_timestamp: int, enabled_at: str
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT OR IGNORE INTO snapshot_tracking
                (mint,launch_timestamp,enabled_at,ended_at) VALUES (?,?,?,NULL)""",
                (mint, launch_timestamp, enabled_at),
            )

    def end_snapshot_tracking(self, ended_at: int) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE snapshot_tracking SET ended_at=? WHERE ended_at IS NULL",
                (ended_at,),
            )

    def tracked_launches(self) -> dict[str, int]:
        with self._lock:
            return {
                row["mint"]: int(row["launch_timestamp"])
                for row in self._connection.execute(
                    "SELECT mint,launch_timestamp FROM snapshot_tracking"
                    " WHERE ended_at IS NULL"
                ).fetchall()
            }

    def snapshot(self, mint: str, target_age_seconds: int) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                """SELECT * FROM token_snapshots
                WHERE mint=? AND target_age_seconds=?""",
                (mint, target_age_seconds),
            ).fetchone()

    def wallet_position(self, mint: str, user: str) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                "SELECT * FROM wallet_positions WHERE mint=? AND user_address=?",
                (mint, user),
            ).fetchone()

    def recent_snapshots(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT l.symbol,s.* FROM token_snapshots s
                JOIN pump_launches l USING(mint)
                ORDER BY s.cutoff_timestamp DESC,s.target_age_seconds DESC LIMIT ?""",
                (limit,),
            ).fetchall())

    def top_wallets(self, mint: str, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT *,buy_token_amount-sell_token_amount AS net_token_amount,
                buy_quote_amount-sell_quote_amount AS net_quote_spent
                FROM wallet_positions WHERE mint=?
                ORDER BY buy_quote_amount DESC LIMIT ?""",
                (mint, limit),
            ).fetchall())

    def enqueue_wallet(
        self, address: str, mint: str, reason: str, priority: int,
        created_at: str,
    ) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """INSERT OR IGNORE INTO wallet_analysis_queue
                (address,mint,reason,priority,created_at,updated_at)
                VALUES (?,?,?,?,?,?)""",
                (address, mint, reason, priority, created_at, created_at),
            )
            return cursor.rowcount == 1

    def enqueue_early_buyer(
        self, address: str, mint: str, limit: int, created_at: str,
    ) -> bool:
        if limit <= 0:
            return False
        with self._lock, self._connection:
            count = int(self._connection.execute(
                """SELECT COUNT(DISTINCT address) AS n
                FROM wallet_analysis_queue WHERE mint=? AND reason='EARLY_BUYER'""",
                (mint,),
            ).fetchone()["n"])
            if count >= limit:
                return False
            cursor = self._connection.execute(
                """INSERT OR IGNORE INTO wallet_analysis_queue
                (address,mint,reason,priority,created_at,updated_at)
                VALUES (?,?,'EARLY_BUYER',50,?,?)""",
                (address, mint, created_at, created_at),
            )
            return cursor.rowcount == 1

    def enqueue_transaction_enrichment(
        self, signature: str, mint: str, user_address: str, slot: int,
        event_timestamp: int, trade_age_seconds: int, limit: int,
        created_at: str,
    ) -> bool:
        if limit <= 0:
            return False
        with self._lock, self._connection:
            count = int(self._connection.execute(
                """SELECT COUNT(DISTINCT user_address) AS n
                FROM transaction_enrichment_queue WHERE mint=?""", (mint,)
            ).fetchone()["n"])
            known = self._connection.execute(
                """SELECT 1 FROM transaction_enrichment_queue
                WHERE signature=?""", (signature,)
            ).fetchone()
            if known or count >= limit:
                return False
            cursor = self._connection.execute(
                """INSERT OR IGNORE INTO transaction_enrichment_queue (
                signature,mint,user_address,slot,event_timestamp,
                trade_age_seconds,priority,created_at,updated_at)
                VALUES (?,?,?,?,?,?,100,?,?)""",
                (signature, mint, user_address, slot, event_timestamp,
                 trade_age_seconds, created_at, created_at),
            )
            return cursor.rowcount == 1

    def claim_transaction_enrichment(self, now_timestamp: int) -> sqlite3.Row | None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            row = self._connection.execute(
                """SELECT * FROM transaction_enrichment_queue
                WHERE status='PENDING' AND next_attempt_at<=?
                ORDER BY priority DESC,id LIMIT 1""", (now_timestamp,)
            ).fetchone()
            if row is None:
                return None
            self._connection.execute(
                """UPDATE transaction_enrichment_queue SET status='RUNNING',
                attempts=attempts+1,updated_at=? WHERE id=?""", (now, row["id"])
            )
            return row

    def save_transaction_evidence(
        self, queue_id: int, item: dict[str, object], evidence: dict[str, object],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO early_trade_metadata (
                signature,mint,user_address,slot,event_timestamp,trade_age_seconds,
                analyzed_at,fee_payer,transaction_fee_lamports,
                compute_units_consumed,compute_unit_limit,
                compute_unit_price_micro_lamports,estimated_priority_fee_lamports,
                jito_tip_lamports,jito_tip_account,jitodontfront_present)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(signature) DO UPDATE SET analyzed_at=excluded.analyzed_at,
                fee_payer=excluded.fee_payer,
                transaction_fee_lamports=excluded.transaction_fee_lamports,
                compute_units_consumed=excluded.compute_units_consumed,
                compute_unit_limit=excluded.compute_unit_limit,
                compute_unit_price_micro_lamports=excluded.compute_unit_price_micro_lamports,
                estimated_priority_fee_lamports=excluded.estimated_priority_fee_lamports,
                jito_tip_lamports=excluded.jito_tip_lamports,
                jito_tip_account=excluded.jito_tip_account,
                jitodontfront_present=excluded.jitodontfront_present""",
                (item["signature"], item["mint"], item["user_address"],
                 item["slot"], item["event_timestamp"], item["trade_age_seconds"],
                 now, evidence["fee_payer"], evidence["transaction_fee_lamports"],
                 evidence["compute_units_consumed"], evidence["compute_unit_limit"],
                 evidence["compute_unit_price_micro_lamports"],
                 evidence["estimated_priority_fee_lamports"],
                 evidence["jito_tip_lamports"], evidence["jito_tip_account"],
                 int(bool(evidence["jitodontfront_present"]))),
            )
            self._connection.execute(
                """UPDATE transaction_enrichment_queue SET status='DONE',
                updated_at=?,last_error=NULL WHERE id=?""", (now, queue_id)
            )

    def fail_transaction_enrichment(
        self, queue_id: int, error: str, next_attempt_at: int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute(
                """UPDATE transaction_enrichment_queue SET status='PENDING',
                updated_at=?,next_attempt_at=?,last_error=? WHERE id=?""",
                (now, next_attempt_at, error[:500], queue_id),
            )

    def sniper_feature_rows(self, mint: str) -> list[dict[str, object]]:
        with self._lock:
            base = self._connection.execute(
                """SELECT mint,user_address,MIN(trade_age_seconds) first_age,
                MIN(slot) first_slot FROM transaction_enrichment_queue
                WHERE mint=? GROUP BY mint,user_address""", (mint,)
            ).fetchall()
            result: list[dict[str, object]] = []
            for row in base:
                user = row["user_address"]
                same_slot = self._connection.execute(
                    """SELECT COUNT(DISTINCT user_address) n FROM pump_trades
                    WHERE mint=? AND slot=? AND is_buy=1""",
                    (mint, row["first_slot"]),
                ).fetchone()["n"]
                behavior = self._connection.execute(
                    """SELECT early_launch_count FROM wallet_behavior_stats
                    WHERE address=?""", (user,)
                ).fetchone()
                repeated = behavior["early_launch_count"] if behavior else 0
                quick = self._connection.execute(
                    """SELECT MIN(t.event_timestamp-l.event_timestamp) seconds
                    FROM pump_trades t JOIN pump_launches l ON l.mint=t.mint
                    WHERE t.mint=? AND t.user_address=? AND t.is_buy=0""",
                    (mint, user),
                ).fetchone()["seconds"]
                profile = self._connection.execute(
                    "SELECT likely_funder FROM wallet_profiles WHERE address=?",
                    (user,),
                ).fetchone()
                funder_peers = 0
                if profile and profile["likely_funder"]:
                    funder_peers = max(0, int(self._connection.execute(
                        """SELECT COUNT(DISTINCT q.address)-1 n
                        FROM wallet_analysis_queue q JOIN wallet_profiles p
                        ON p.address=q.address WHERE q.mint=?
                        AND p.likely_funder=?""",
                        (mint, profile["likely_funder"]),
                    ).fetchone()["n"]))
                metadata = self._connection.execute(
                    """SELECT * FROM early_trade_metadata
                    WHERE mint=? AND user_address=? ORDER BY event_timestamp LIMIT 1""",
                    (mint, user),
                ).fetchone()
                fee_payer_peers = 0
                if metadata and metadata["fee_payer"]:
                    fee_payer_peers = max(0, int(self._connection.execute(
                        """SELECT COUNT(DISTINCT user_address)-1 n
                        FROM early_trade_metadata WHERE mint=? AND slot=?
                        AND fee_payer=?""",
                        (mint, metadata["slot"], metadata["fee_payer"]),
                    ).fetchone()["n"]))
                result.append({
                    "mint": mint, "user_address": user,
                    "first_buy_age_seconds": int(row["first_age"]),
                    "same_slot_early_buyers": int(same_slot),
                    "repeated_early_launches": int(repeated),
                    "quick_sell_seconds": quick,
                    "same_funder_peers": funder_peers,
                    "same_fee_payer_peers": fee_payer_peers,
                    "jito_tip_lamports": int(metadata["jito_tip_lamports"])
                    if metadata else 0,
                    "priority_fee_lamports": metadata["estimated_priority_fee_lamports"]
                    if metadata else None,
                    "transaction_analyzed": int(metadata is not None),
                    "wallet_analyzed": int(profile is not None),
                    "jitodontfront_present": int(metadata["jitodontfront_present"])
                    if metadata else 0,
                })
            return result

    def save_sniper_score(self, values: dict[str, object]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO sniper_scores (
                mint,user_address,calculated_at,score,classification,confidence,
                first_buy_age_seconds,same_slot_early_buyers,
                repeated_early_launches,quick_sell_seconds,same_funder_peers,
                same_fee_payer_peers,jito_routed,jito_tip_lamports,
                priority_fee_lamports,bundle_likelihood,reasons_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(mint,user_address) DO UPDATE SET
                calculated_at=excluded.calculated_at,score=excluded.score,
                classification=excluded.classification,confidence=excluded.confidence,
                first_buy_age_seconds=excluded.first_buy_age_seconds,
                same_slot_early_buyers=excluded.same_slot_early_buyers,
                repeated_early_launches=excluded.repeated_early_launches,
                quick_sell_seconds=excluded.quick_sell_seconds,
                same_funder_peers=excluded.same_funder_peers,
                same_fee_payer_peers=excluded.same_fee_payer_peers,
                jito_routed=excluded.jito_routed,
                jito_tip_lamports=excluded.jito_tip_lamports,
                priority_fee_lamports=excluded.priority_fee_lamports,
                bundle_likelihood=excluded.bundle_likelihood,
                reasons_json=excluded.reasons_json""",
                (values["mint"], values["user_address"], now, values["score"],
                 values["classification"], values["confidence"],
                 values["first_buy_age_seconds"], values["same_slot_early_buyers"],
                 values["repeated_early_launches"], values["quick_sell_seconds"],
                 values["same_funder_peers"], values["same_fee_payer_peers"],
                 int(bool(values["jito_routed"])), values["jito_tip_lamports"],
                 values["priority_fee_lamports"], values["bundle_likelihood"],
                 json.dumps(values["reasons"], ensure_ascii=False)),
            )

    def rebuild_wallet_behavior_stats(self) -> int:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM wallet_behavior_stats")
            cursor = self._connection.execute(
                """INSERT INTO wallet_behavior_stats
                (address,early_launch_count,updated_at)
                SELECT w.user_address,COUNT(*),?
                FROM wallet_positions w JOIN pump_launches l ON l.mint=w.mint
                WHERE w.buy_count>0 AND w.first_trade_timestamp-l.event_timestamp
                BETWEEN 0 AND 10 GROUP BY w.user_address""", (now,)
            )
            return cursor.rowcount

    def sniper_scores(self, mint: str | None = None, limit: int = 50) -> list[sqlite3.Row]:
        where = "WHERE s.mint=?" if mint else ""
        params: tuple[object, ...] = (mint, limit) if mint else (limit,)
        with self._lock:
            return list(self._connection.execute(
                f"""SELECT l.symbol,s.* FROM sniper_scores s
                JOIN pump_launches l ON l.mint=s.mint {where}
                ORDER BY s.score DESC,s.calculated_at DESC LIMIT ?""", params
            ).fetchall())

    def claim_wallet_analysis(self, now_timestamp: int) -> sqlite3.Row | None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            row = self._connection.execute(
                """SELECT q.* FROM wallet_analysis_queue q
                LEFT JOIN wallet_profiles p ON p.address=q.address
                WHERE q.status='PENDING' AND q.next_attempt_at<=?
                AND p.address IS NULL
                ORDER BY q.priority DESC,q.id LIMIT 1""",
                (now_timestamp,),
            ).fetchone()
            if row is None:
                return None
            self._connection.execute(
                """UPDATE wallet_analysis_queue SET status='RUNNING',
                attempts=attempts+1,updated_at=? WHERE id=?""", (now, row["id"])
            )
            return row

    def save_wallet_analysis(
        self, queue_id: int, address: str, signatures_scanned: int,
        history_complete: bool, oldest_signature: str | None,
        oldest_block_time: int | None, funder: str | None,
        funding_signature: str | None, funding_lamports: int | None,
        funding_block_time: int | None, funding_label: str | None,
        confidence: float,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO wallet_profiles (
                address,analyzed_at,signatures_scanned,history_complete,
                oldest_scanned_signature,oldest_scanned_block_time,likely_funder,
                funding_signature,funding_lamports,funding_block_time,funding_label,
                confidence) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(address) DO UPDATE SET
                analyzed_at=excluded.analyzed_at,
                signatures_scanned=excluded.signatures_scanned,
                history_complete=excluded.history_complete,
                oldest_scanned_signature=excluded.oldest_scanned_signature,
                oldest_scanned_block_time=excluded.oldest_scanned_block_time,
                likely_funder=excluded.likely_funder,
                funding_signature=excluded.funding_signature,
                funding_lamports=excluded.funding_lamports,
                funding_block_time=excluded.funding_block_time,
                funding_label=excluded.funding_label,confidence=excluded.confidence""",
                (address, now, signatures_scanned, int(history_complete),
                 oldest_signature, oldest_block_time, funder, funding_signature,
                 funding_lamports, funding_block_time, funding_label, confidence),
            )
            if funder and funding_signature and funding_lamports:
                edge_type = "FUNDED_BY" if history_complete else "RECENT_INBOUND_CANDIDATE"
                self._connection.execute(
                    """INSERT OR REPLACE INTO wallet_edges
                    (source_address,target_address,edge_type,signature,block_time,
                    lamports,confidence) VALUES (?,?,?,?,?,?,?)""",
                    (funder, address, edge_type, funding_signature,
                     funding_block_time, funding_lamports, confidence),
                )
            self._connection.execute(
                """UPDATE wallet_analysis_queue SET status='DONE',updated_at=?,
                last_error=NULL WHERE address=? AND status IN ('PENDING','RUNNING')""",
                (now, address),
            )

    def fail_wallet_analysis(
        self, queue_id: int, error: str, next_attempt_at: int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute(
                """UPDATE wallet_analysis_queue SET status='PENDING',updated_at=?,
                next_attempt_at=?,last_error=? WHERE id=?""",
                (now, next_attempt_at, error[:500], queue_id),
            )

    def wallet_profile(self, address: str) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                "SELECT * FROM wallet_profiles WHERE address=?", (address,)
            ).fetchone()

    def creator_history(self, creator: str) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                """SELECT l.creator,COUNT(*) AS launch_count,
                (SELECT COUNT(DISTINCT s.mint) FROM token_snapshots s
                 JOIN pump_launches x ON x.mint=s.mint
                 WHERE x.creator=l.creator AND s.creator_sold=1)
                 AS creator_sold_token_count,
                (SELECT COUNT(DISTINCT t.mint) FROM pump_trades t
                 JOIN pump_launches x ON x.mint=t.mint
                 WHERE x.creator=l.creator) AS locally_traded_token_count,
                (SELECT COUNT(*) FROM pump_trades t
                 JOIN pump_launches x ON x.mint=t.mint
                 WHERE x.creator=l.creator AND t.user_address=l.creator
                 AND t.is_buy=0) AS creator_sell_count
                FROM pump_launches l WHERE l.creator=? GROUP BY l.creator""",
                (creator,),
            ).fetchone()

    def recent_creator_histories(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT creator,COUNT(*) AS launch_count,
                MIN(event_timestamp) AS first_launch_timestamp,
                MAX(event_timestamp) AS latest_launch_timestamp
                FROM pump_launches GROUP BY creator
                ORDER BY latest_launch_timestamp DESC LIMIT ?""", (limit,)
            ).fetchall())

    def risk_feature_rows(
        self, mint: str | None = None, only_unscored: bool = False,
    ) -> list[sqlite3.Row]:
        conditions: list[str] = []
        values: list[object] = []
        if mint:
            conditions.append("s.mint=?")
            values.append(mint)
        if only_unscored:
            conditions.append("d.mint IS NULL")
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        query = f"""SELECT s.*,l.creator,l.symbol,
            (SELECT COUNT(*) FROM pump_launches cl WHERE cl.creator=l.creator)
                AS creator_launch_count,
            (SELECT COUNT(DISTINCT cs.mint) FROM token_snapshots cs
             JOIN pump_launches cl ON cl.mint=cs.mint
             WHERE cl.creator=l.creator AND cs.creator_sold=1)
                AS creator_sold_token_count,
            (SELECT COUNT(DISTINCT q.address) FROM wallet_analysis_queue q
             WHERE q.mint=s.mint) AS queued_wallets,
            (SELECT COUNT(DISTINCT q.address) FROM wallet_analysis_queue q
             JOIN wallet_profiles p ON p.address=q.address
             WHERE q.mint=s.mint) AS analyzed_wallets,
            (SELECT COUNT(DISTINCT q2.address)
             FROM wallet_analysis_queue q2
             JOIN wallet_profiles p2 ON p2.address=q2.address
             WHERE q2.mint=s.mint AND p2.likely_funder IS NOT NULL
             AND EXISTS (
                SELECT 1 FROM wallet_analysis_queue q3
                JOIN wallet_profiles p3 ON p3.address=q3.address
                WHERE q3.mint=s.mint AND q3.address<>q2.address
                AND p3.likely_funder=p2.likely_funder
             )) AS shared_funder_wallets
            ,COALESCE((SELECT MAX(ss.score) FROM sniper_scores ss
             WHERE ss.mint=s.mint),0) AS max_sniper_score
            ,COALESCE((SELECT COUNT(*) FROM sniper_scores ss
             WHERE ss.mint=s.mint AND ss.classification='COORDINATED_SNIPER'),0)
             AS coordinated_snipers
            ,COALESCE((SELECT COUNT(*) FROM sniper_scores ss
             WHERE ss.mint=s.mint AND ss.bundle_likelihood='HIGH'),0)
             AS high_bundle_likelihood_wallets
            FROM token_snapshots s JOIN pump_launches l ON l.mint=s.mint
            LEFT JOIN risk_decisions d ON d.mint=s.mint
                AND d.snapshot_age_seconds=s.target_age_seconds
            {where}
            ORDER BY s.cutoff_timestamp,s.target_age_seconds"""
        with self._lock:
            return list(self._connection.execute(query, values).fetchall())

    def save_risk_decision(
        self, mint: str, age: int, ruleset_version: str, decision: str,
        risk_score: int, opportunity_score: int, confidence: float,
        reasons: tuple[str, ...], warnings: tuple[str, ...],
        features: dict[str, object],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO risk_decisions (
                mint,snapshot_age_seconds,evaluated_at,ruleset_version,decision,
                risk_score,opportunity_score,confidence,reasons_json,warnings_json,
                features_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(mint,snapshot_age_seconds) DO UPDATE SET
                evaluated_at=excluded.evaluated_at,
                ruleset_version=excluded.ruleset_version,
                decision=excluded.decision,risk_score=excluded.risk_score,
                opportunity_score=excluded.opportunity_score,
                confidence=excluded.confidence,reasons_json=excluded.reasons_json,
                warnings_json=excluded.warnings_json,
                features_json=excluded.features_json""",
                (mint, age, now, ruleset_version, decision, risk_score,
                 opportunity_score, confidence,
                 json.dumps(reasons, ensure_ascii=False),
                 json.dumps(warnings, ensure_ascii=False),
                 json.dumps(features, ensure_ascii=False)),
            )

    def recent_risk_decisions(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT l.symbol,d.* FROM risk_decisions d
                JOIN pump_launches l ON l.mint=d.mint
                ORDER BY d.evaluated_at DESC LIMIT ?""", (limit,)
            ).fetchall())

    def paper_entry_candidates(self) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT d.mint,d.snapshot_age_seconds,s.cutoff_timestamp,
                l.quote_asset,l.event_timestamp,st.ended_at
                FROM risk_decisions d
                JOIN token_snapshots s ON s.mint=d.mint
                 AND s.target_age_seconds=d.snapshot_age_seconds
                JOIN pump_launches l ON l.mint=d.mint
                JOIN snapshot_tracking st ON st.mint=d.mint
                LEFT JOIN paper_positions p ON p.mint=d.mint
                 AND p.decision_age_seconds=d.snapshot_age_seconds
                WHERE d.decision='ADAY' AND p.mint IS NULL
                ORDER BY s.cutoff_timestamp"""
            ).fetchall())

    def first_trade_after(
        self, mint: str, timestamp: int, max_timestamp: int,
    ) -> sqlite3.Row | None:
        with self._lock:
            return self._connection.execute(
                """SELECT * FROM pump_trades WHERE mint=? AND event_timestamp>=?
                AND event_timestamp<=? ORDER BY event_timestamp,slot,event_index
                LIMIT 1""", (mint, timestamp, max_timestamp)
            ).fetchone()

    def has_unresolved_gap(self, start_slot: int, end_slot: int) -> bool:
        with self._lock:
            row = self._connection.execute(
                """SELECT 1 FROM stream_gaps WHERE status<>'BACKFILLED'
                AND start_slot<=? AND end_slot>=? LIMIT 1""",
                (end_slot, start_slot),
            ).fetchone()
        return row is not None

    def max_trade_slot(self, mint: str, start: int, end: int) -> int | None:
        with self._lock:
            row = self._connection.execute(
                """SELECT MAX(slot) AS slot FROM pump_trades
                WHERE mint=? AND event_timestamp BETWEEN ? AND ?""",
                (mint, start, end),
            ).fetchone()
        return int(row["slot"]) if row and row["slot"] is not None else None

    def v2_entry_candidates(self, limit: int = 1000,
                            minimum_cutoff: int | None = None) -> list[sqlite3.Row]:
        recent_filter = "" if minimum_cutoff is None else "AND s.cutoff_timestamp>=?"
        values: tuple[object, ...] = () if minimum_cutoff is None else (minimum_cutoff,)
        with self._lock:
            return list(self._connection.execute(
                f"""SELECT d.mint,d.snapshot_age_seconds,d.decision,
                s.cutoff_timestamp,l.quote_asset,l.event_timestamp,st.ended_at
                FROM risk_decisions d JOIN token_snapshots s ON s.mint=d.mint
                 AND s.target_age_seconds=d.snapshot_age_seconds
                JOIN pump_launches l ON l.mint=d.mint
                JOIN snapshot_tracking st ON st.mint=d.mint
                LEFT JOIN paper_v2_positions p ON p.mint=d.mint
                 AND p.decision_age_seconds=d.snapshot_age_seconds
                WHERE d.snapshot_age_seconds IN (10,30,60) AND p.mint IS NULL
                {recent_filter}
                ORDER BY s.cutoff_timestamp,d.snapshot_age_seconds LIMIT ?""",
                values + (limit,)).fetchall())

    def save_v2_position(self, candidate: sqlite3.Row, result: dict[str, object],
                         trade: sqlite3.Row | None, assumptions: dict[str, object],
                         canonical: bool, deadline: int) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock:
            self._connection.execute(
                """INSERT OR IGNORE INTO paper_v2_positions VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (candidate["mint"], candidate["snapshot_age_seconds"],
                 f'AGE_{candidate["snapshot_age_seconds"]}', int(canonical), "2.0",
                 now, result["status"], result.get("reason"),
                 candidate["cutoff_timestamp"], deadline,
                 trade["signature"] if trade else None,
                 trade["event_timestamp"] if trade else None,
                 trade["slot"] if trade else None, assumptions["notional_quote"],
                 candidate["quote_asset"], result.get("entry_price"),
                 result.get("token_quantity"), result.get("entry_fee", assumptions["one_way_fee"]),
                 result.get("protocol_fee_bps"), result.get("estimated_impact_bps"),
                 result.get("entry_quote_reserve"), result.get("entry_token_reserve"),
                 json.dumps(assumptions, ensure_ascii=False)))

    def has_canonical_v2(self, mint: str) -> bool:
        with self._lock:
            return self._connection.execute(
                "SELECT 1 FROM paper_v2_positions WHERE mint=? AND is_canonical=1",
                (mint,),
            ).fetchone() is not None

    def v2_open_positions(self, now: int, horizon: int, recompute: bool,
                          limit: int = 2000,
                          minimum_entry: int | None = None) -> list[sqlite3.Row]:
        extra = "" if recompute else "AND o.mint IS NULL"
        recent_filter = "" if minimum_entry is None else "AND p.entry_timestamp>=?"
        recent_values: tuple[object, ...] = () if minimum_entry is None else (minimum_entry,)
        with self._lock:
            return list(self._connection.execute(
                f"""SELECT p.*,d.decision,st.ended_at FROM paper_v2_positions p
                JOIN risk_decisions d ON d.mint=p.mint
                 AND d.snapshot_age_seconds=p.decision_age_seconds
                JOIN snapshot_tracking st ON st.mint=p.mint
                LEFT JOIN executable_outcomes_v2 o ON o.mint=p.mint
                 AND o.decision_age_seconds=p.decision_age_seconds
                 AND o.horizon_seconds=?
                WHERE p.status='OPEN' AND p.entry_timestamp+?<=? {extra}
                {recent_filter}
                AND (st.ended_at IS NULL OR st.ended_at>=p.entry_timestamp+?)
                ORDER BY p.entry_timestamp LIMIT ?""",
                (horizon, horizon, now) + recent_values + (horizon, limit)).fetchall())

    def save_v2_outcome(self, position: sqlite3.Row, horizon: int,
                        result: dict[str, object], strategy: dict[str, object],
                        quality: str) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock:
            self._connection.execute(
                """INSERT INTO executable_outcomes_v2 VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(mint,decision_age_seconds,horizon_seconds) DO UPDATE SET
                evaluated_at=excluded.evaluated_at,sample_count=excluded.sample_count,
                max_x=excluded.max_x,min_x=excluded.min_x,final_x=excluded.final_x,
                strategy_x=excluded.strategy_x,exit_reason=excluded.exit_reason,
                max_drawdown_pct=excluded.max_drawdown_pct,
                hit_1_5x=excluded.hit_1_5x,hit_2x=excluded.hit_2x,
                hit_3x=excluded.hit_3x,hit_5x=excluded.hit_5x,
                data_quality=excluded.data_quality,tranches_json=excluded.tranches_json""",
                (position["mint"], position["decision_age_seconds"], horizon,
                 position["decision"], position["is_canonical"], now,
                 result["sample_count"], result["max_x"], result["min_x"],
                 result["final_x"], strategy["strategy_x"], strategy["exit_reason"],
                 result["max_drawdown_pct"], int(result["hit_1_5x"]),
                 int(result["hit_2x"]), int(result["hit_3x"]), int(result["hit_5x"]),
                 quality, json.dumps(strategy["tranches"], ensure_ascii=False)))

    def commit(self) -> None:
        with self._lock:
            self._connection.commit()

    def recent_v2_outcomes(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT l.symbol,o.* FROM executable_outcomes_v2 o
                JOIN pump_launches l ON l.mint=o.mint
                ORDER BY o.evaluated_at DESC LIMIT ?""", (limit,)).fetchall())

    def save_paper_position(
        self, candidate: sqlite3.Row, result: dict[str, object],
        trade: sqlite3.Row | None, assumptions: dict[str, object],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT OR IGNORE INTO paper_positions (
                mint,decision_age_seconds,created_at,status,failure_reason,
                decision_cutoff_timestamp,entry_signature,entry_event_index,
                entry_timestamp,entry_slot,notional_quote,quote_asset,
                entry_price_quote_per_raw_token,token_quantity_raw,entry_fee,
                estimated_impact_bps,assumptions_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (candidate["mint"], candidate["snapshot_age_seconds"], now,
                 result["status"], result.get("reason"),
                 candidate["cutoff_timestamp"],
                 trade["signature"] if trade else None,
                 trade["event_index"] if trade else None,
                 trade["event_timestamp"] if trade else None,
                 trade["slot"] if trade else None,
                 assumptions["notional_quote"], candidate["quote_asset"],
                 result.get("entry_price"), result.get("token_quantity"),
                 result.get("entry_fee", assumptions["one_way_fee"]),
                 result.get("estimated_impact_bps"),
                 json.dumps(assumptions, ensure_ascii=False)),
            )

    def due_paper_positions(
        self, now_timestamp: int, horizon: int, include_existing: bool = False,
    ) -> list[sqlite3.Row]:
        existing_filter = "" if include_existing else "AND o.mint IS NULL"
        with self._lock:
            return list(self._connection.execute(
                f"""SELECT p.*,st.ended_at FROM paper_positions p
                JOIN snapshot_tracking st ON st.mint=p.mint
                LEFT JOIN paper_outcomes o ON o.mint=p.mint
                 AND o.decision_age_seconds=p.decision_age_seconds
                 AND o.horizon_seconds=?
                WHERE p.status='OPEN' AND p.entry_timestamp IS NOT NULL
                {existing_filter} AND p.entry_timestamp+?<=?
                AND (st.ended_at IS NULL OR st.ended_at>=p.entry_timestamp+?)""",
                (horizon, horizon, now_timestamp, horizon),
            ).fetchall())

    def trades_for_paper_outcome(
        self, mint: str, start_timestamp: int, end_timestamp: int,
    ) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT * FROM pump_trades WHERE mint=? AND event_timestamp>=?
                AND event_timestamp<=? ORDER BY event_timestamp,slot,event_index""",
                (mint, start_timestamp, end_timestamp),
            ).fetchall())

    def save_paper_outcome(
        self, position: sqlite3.Row, horizon: int, result: dict[str, object],
        data_quality: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO paper_outcomes (
                mint,decision_age_seconds,horizon_seconds,evaluated_at,
                sample_count,max_x,min_x,final_x,max_drawdown_pct,hit_1_5x,
                hit_2x,hit_3x,hit_5x,data_quality)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(mint,decision_age_seconds,horizon_seconds) DO UPDATE SET
                evaluated_at=excluded.evaluated_at,
                sample_count=excluded.sample_count,max_x=excluded.max_x,
                min_x=excluded.min_x,final_x=excluded.final_x,
                max_drawdown_pct=excluded.max_drawdown_pct,
                hit_1_5x=excluded.hit_1_5x,hit_2x=excluded.hit_2x,
                hit_3x=excluded.hit_3x,hit_5x=excluded.hit_5x,
                data_quality=excluded.data_quality""",
                (position["mint"], position["decision_age_seconds"], horizon,
                 now, result["sample_count"], result["max_x"], result["min_x"],
                 result["final_x"], result["max_drawdown_pct"],
                 int(result["hit_1_5x"]), int(result["hit_2x"]),
                 int(result["hit_3x"]), int(result["hit_5x"]), data_quality),
            )

    def recent_paper_positions(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT l.symbol,p.* FROM paper_positions p
                JOIN pump_launches l ON l.mint=p.mint
                ORDER BY p.created_at DESC LIMIT ?""", (limit,)
            ).fetchall())

    def recent_paper_outcomes(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT l.symbol,o.* FROM paper_outcomes o
                JOIN pump_launches l ON l.mint=o.mint
                ORDER BY o.evaluated_at DESC LIMIT ?""", (limit,)
            ).fetchall())

    def due_market_outcomes(
        self, now_timestamp: int, horizon: int, latency_seconds: int,
        include_existing: bool = False,
    ) -> list[sqlite3.Row]:
        existing_filter = "" if include_existing else "AND o.mint IS NULL"
        with self._lock:
            return list(self._connection.execute(
                f"""SELECT d.mint,d.snapshot_age_seconds,s.cutoff_timestamp,
                l.event_timestamp,st.ended_at
                FROM risk_decisions d
                JOIN token_snapshots s ON s.mint=d.mint
                 AND s.target_age_seconds=d.snapshot_age_seconds
                JOIN pump_launches l ON l.mint=d.mint
                JOIN snapshot_tracking st ON st.mint=d.mint
                LEFT JOIN market_outcomes o ON o.mint=d.mint
                 AND o.decision_age_seconds=d.snapshot_age_seconds
                 AND o.horizon_seconds=?
                WHERE s.cutoff_timestamp+?+?<=? {existing_filter}
                AND (st.ended_at IS NULL OR
                 st.ended_at>=s.cutoff_timestamp+?+?)""",
                (horizon, latency_seconds, horizon, now_timestamp,
                 latency_seconds, horizon),
            ).fetchall())

    def save_market_outcome(
        self, candidate: sqlite3.Row, horizon: int, reference: sqlite3.Row,
        result: dict[str, object],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO market_outcomes (
                mint,decision_age_seconds,horizon_seconds,evaluated_at,
                reference_signature,reference_timestamp,sample_count,max_market_x,
                min_market_x,final_market_x,hit_1_5x,hit_2x,hit_3x,hit_5x,
                data_quality) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(mint,decision_age_seconds,horizon_seconds) DO UPDATE SET
                evaluated_at=excluded.evaluated_at,
                reference_signature=excluded.reference_signature,
                reference_timestamp=excluded.reference_timestamp,
                sample_count=excluded.sample_count,max_market_x=excluded.max_market_x,
                min_market_x=excluded.min_market_x,
                final_market_x=excluded.final_market_x,
                hit_1_5x=excluded.hit_1_5x,hit_2x=excluded.hit_2x,
                hit_3x=excluded.hit_3x,hit_5x=excluded.hit_5x,
                data_quality=excluded.data_quality""",
                (candidate["mint"], candidate["snapshot_age_seconds"], horizon,
                 now, reference["signature"], reference["event_timestamp"],
                 result["sample_count"], result["max_market_x"],
                 result["min_market_x"], result["final_market_x"],
                 int(result["hit_1_5x"]), int(result["hit_2x"]),
                 int(result["hit_3x"]), int(result["hit_5x"]), "CONTINUOUS"),
            )

    def recent_market_outcomes(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT l.symbol,d.decision,o.* FROM market_outcomes o
                JOIN pump_launches l ON l.mint=o.mint
                JOIN risk_decisions d ON d.mint=o.mint
                 AND d.snapshot_age_seconds=o.decision_age_seconds
                ORDER BY o.evaluated_at DESC LIMIT ?""", (limit,)
            ).fetchall())

    def create_due_snapshots(self, now_timestamp: int) -> int:
        targets = (2, 5, 10, 30, 60)
        created = 0
        with self._lock:
            launches = self._connection.execute(
                """SELECT mint,creator,event_timestamp,virtual_quote_reserves,
                virtual_sol_reserves,virtual_token_reserves,quote_asset
                FROM pump_launches JOIN snapshot_tracking USING(mint)
                WHERE event_timestamp<=?""",
                (now_timestamp - min(targets),),
            ).fetchall()
            existing = {
                (row["mint"], row["target_age_seconds"])
                for row in self._connection.execute(
                    "SELECT mint,target_age_seconds FROM token_snapshots"
                ).fetchall()
            }
            for launch in launches:
                for age in targets:
                    if (launch["mint"], age) in existing:
                        continue
                    cutoff = int(launch["event_timestamp"]) + age
                    if cutoff > now_timestamp:
                        continue
                    tracking = self._connection.execute(
                        "SELECT ended_at FROM snapshot_tracking WHERE mint=?",
                        (launch["mint"],),
                    ).fetchone()
                    if tracking and tracking["ended_at"] is not None and (
                        cutoff > int(tracking["ended_at"])
                    ):
                        continue
                    self._create_snapshot(launch, age, cutoff, now_timestamp)
                    created += 1
        return created

    def _create_snapshot(
        self, launch: sqlite3.Row, age: int, cutoff: int, now_timestamp: int
    ) -> None:
        trades = self._connection.execute(
            """SELECT * FROM pump_trades WHERE mint=? AND event_timestamp>=?
            AND event_timestamp<=? ORDER BY event_timestamp,slot,event_index""",
            (launch["mint"], launch["event_timestamp"], cutoff),
        ).fetchall()
        buys = [row for row in trades if row["is_buy"]]
        sells = [row for row in trades if not row["is_buy"]]
        buyer_totals: dict[str, int] = {}
        for row in buys:
            buyer_totals[row["user_address"]] = (
                buyer_totals.get(row["user_address"], 0) + row["quote_amount"]
            )
        buy_quote = sum(row["quote_amount"] for row in buys)
        sell_quote = sum(row["quote_amount"] for row in sells)
        ranked = sorted(buyer_totals.values(), reverse=True)
        top_share = ranked[0] / buy_quote if buy_quote and ranked else 0.0
        top5_share = sum(ranked[:5]) / buy_quote if buy_quote else 0.0
        creator_sold = any(
            row["user_address"] == launch["creator"] for row in sells
        )
        latest = trades[-1] if trades else None
        virtual_quote = (
            latest["virtual_quote_reserves"] or latest["virtual_sol_reserves"]
            if latest else launch["virtual_quote_reserves"] or launch["virtual_sol_reserves"]
        )
        virtual_token = (
            latest["virtual_token_reserves"] if latest
            else launch["virtual_token_reserves"]
        )
        price = None
        if virtual_token and launch["quote_asset"] == "SOL":
            price = (virtual_quote / 1_000_000_000) / (virtual_token / 1_000_000)
        generated_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        delay_ms = max(0, (now_timestamp - cutoff) * 1000)
        quality = "ON_TIME" if delay_ms <= 1500 else "LATE"
        with self._connection:
            self._connection.execute(
                """INSERT OR IGNORE INTO token_snapshots (
                mint,target_age_seconds,cutoff_timestamp,generated_at,
                generation_delay_ms,trade_count,unique_buyers,unique_sellers,
                buy_quote_amount,sell_quote_amount,net_quote_flow,buy_token_amount,
                sell_token_amount,top_buyer_share,top5_buyer_share,creator_sold,
                latest_virtual_quote_reserves,latest_virtual_token_reserves,
                price_quote_per_token,snapshot_quality)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (launch["mint"], age, cutoff, generated_at, delay_ms, len(trades),
                 len({row["user_address"] for row in buys}),
                 len({row["user_address"] for row in sells}), buy_quote,
                 sell_quote, buy_quote - sell_quote,
                 sum(row["token_amount"] for row in buys),
                 sum(row["token_amount"] for row in sells), top_share, top5_share,
                 int(creator_sold), virtual_quote, virtual_token, price, quality),
            )

    def save_gap(self, gap: SlotGap) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT OR IGNORE INTO stream_gaps
                (start_slot,end_slot,detected_at,provider_name,status,detail)
                VALUES (?,?,?,?,?,?)""",
                (gap.start_slot, gap.end_slot, gap.detected_at,
                 gap.provider_name, gap.status, gap.detail),
            )

    def update_gap(self, start: int, end: int, status: str, detail: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """UPDATE stream_gaps SET status=?, detail=?
                WHERE start_slot=? AND end_slot=?""",
                (status, detail, start, end),
            )

    def get_state_int(self, key: str) -> int | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM service_state WHERE key=?", (key,)
            ).fetchone()
        return int(row["value"]) if row else None

    def set_state(self, key: str, value: str | int) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO service_state(key,value) VALUES (?,?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (key, str(value)),
            )

    def counts(self) -> dict[str, int]:
        with self._lock:
            return {
                table: int(self._connection.execute(
                    f"SELECT COUNT(*) AS n FROM {table}"
                ).fetchone()["n"])
                for table in (
                    "chain_events", "tokens_minimal", "pump_launches", "pump_trades",
                    "wallet_positions", "snapshot_tracking", "token_snapshots",
                    "stream_gaps", "wallet_analysis_queue", "wallet_profiles",
                    "wallet_edges", "risk_decisions", "paper_positions",
                    "paper_outcomes", "market_outcomes",
                    "transaction_enrichment_queue", "early_trade_metadata",
                    "sniper_scores", "wallet_behavior_stats",
                    "paper_v2_positions", "executable_outcomes_v2",
                    "x_band_calibration"
                )
            }

    def calibration_source(self, horizon: int) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT o.*,d.risk_score,d.opportunity_score
                FROM executable_outcomes_v2 o JOIN risk_decisions d
                 ON d.mint=o.mint AND d.snapshot_age_seconds=o.decision_age_seconds
                WHERE o.horizon_seconds=? AND o.data_quality='CONTINUOUS'""",
                (horizon,)).fetchall())

    def replace_calibrations(self, horizon: int, rows: list[tuple[object, ...]]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM x_band_calibration WHERE horizon_seconds=?", (horizon,))
            self._connection.executemany(
                """INSERT INTO x_band_calibration VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [tuple(row) + (now,) for row in rows])

    def calibrations(self, horizon: int, limit: int) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT * FROM x_band_calibration WHERE horizon_seconds=?
                ORDER BY p90_x DESC,sample_count DESC LIMIT ?""", (horizon, limit)).fetchall())

    def missed_watchlist(self, horizon: int, minimum_x: float, limit: int) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT l.symbol,o.mint,o.decision_age_seconds,o.max_x,o.final_x,
                o.strategy_x,d.risk_score,d.opportunity_score,d.reasons_json,
                d.warnings_json,d.features_json
                FROM executable_outcomes_v2 o JOIN risk_decisions d
                 ON d.mint=o.mint AND d.snapshot_age_seconds=o.decision_age_seconds
                JOIN pump_launches l ON l.mint=o.mint
                WHERE o.horizon_seconds=? AND o.decision='IZLE'
                 AND o.data_quality='CONTINUOUS' AND o.max_x>=?
                ORDER BY o.max_x DESC LIMIT ?""", (horizon, minimum_x, limit)).fetchall())

    def raw_events(self) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._connection.execute(
                """SELECT signature,slot,program_id,block_time,client_received_at,
                data_completeness,raw_transaction_json FROM chain_events
                WHERE raw_transaction_json IS NOT NULL ORDER BY slot,signature"""
            ).fetchall())

    def reconcile_pump_tokens(self, program_id: str) -> int:
        """Eski extractor'dan kalan, launch ile dogrulanmamis mintleri siler."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """DELETE FROM tokens_minimal
                WHERE program_id=? AND mint NOT IN (SELECT mint FROM pump_launches)""",
                (program_id,),
            )
            return cursor.rowcount

    def reconcile_trade_scope(self, max_age_seconds: int) -> int:
        """Yalniz izlenen launch penceresindeki trade ve walletlari yeniden kurar."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """DELETE FROM pump_trades WHERE NOT EXISTS (
                SELECT 1 FROM snapshot_tracking s WHERE s.mint=pump_trades.mint
                AND pump_trades.event_timestamp>=s.launch_timestamp
                AND pump_trades.event_timestamp<=s.launch_timestamp+?)""",
                (max_age_seconds,),
            )
            self._connection.execute("DELETE FROM wallet_positions")
            self._connection.execute(
                """INSERT INTO wallet_positions (
                mint,user_address,buy_token_amount,sell_token_amount,
                buy_quote_amount,sell_quote_amount,buy_count,sell_count,
                first_trade_timestamp,last_trade_timestamp)
                SELECT mint,user_address,
                SUM(CASE WHEN is_buy=1 THEN token_amount ELSE 0 END),
                SUM(CASE WHEN is_buy=0 THEN token_amount ELSE 0 END),
                SUM(CASE WHEN is_buy=1 THEN quote_amount ELSE 0 END),
                SUM(CASE WHEN is_buy=0 THEN quote_amount ELSE 0 END),
                SUM(CASE WHEN is_buy=1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN is_buy=0 THEN 1 ELSE 0 END),
                MIN(event_timestamp),MAX(event_timestamp)
                FROM pump_trades GROUP BY mint,user_address"""
            )
            self._connection.execute(
                "DELETE FROM token_snapshots WHERE mint NOT IN (SELECT mint FROM snapshot_tracking)"
            )
            self._connection.execute(
                """DELETE FROM chain_events WHERE raw_transaction_json IS NULL
                AND signature NOT IN (SELECT signature FROM pump_trades)"""
            )
            for row in self._connection.execute(
                """SELECT signature,logs_json FROM chain_events
                WHERE raw_transaction_json IS NULL"""
            ).fetchall():
                logs = json.loads(row["logs_json"])
                compact = [line for line in logs if line.startswith("Program data: ")]
                self._connection.execute(
                    "UPDATE chain_events SET logs_json=? WHERE signature=?",
                    (json.dumps(compact), row["signature"]),
                )
            return cursor.rowcount
