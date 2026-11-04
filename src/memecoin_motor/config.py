from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True, slots=True)
class Settings:
    solana_http_url: str
    solana_ws_url: str
    launch_program_id: str | None
    database_path: Path
    commitment: str
    max_backfill_slots: int
    rpc_timeout_seconds: float
    reconnect_max_seconds: float
    trade_track_seconds: int
    wallet_enrichment_enabled: bool
    wallet_early_buyer_limit: int
    wallet_signature_page_size: int
    wallet_max_signature_pages: int
    wallet_rpc_interval_seconds: float
    paper_enabled: bool
    paper_notional_lamports: int
    paper_latency_seconds: int
    paper_slippage_bps: int
    paper_base_fee_lamports: int
    paper_priority_fee_lamports: int
    paper_jito_tip_lamports: int
    paper_max_reserve_impact_bps: int
    paper_max_fill_wait_seconds: int
    sniper_enabled: bool
    sniper_early_buyer_limit: int
    sniper_max_trade_age_seconds: int
    sniper_rpc_interval_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        commitment = os.getenv("COMMITMENT", "confirmed").lower()
        if commitment not in {"processed", "confirmed", "finalized"}:
            raise ValueError("COMMITMENT processed, confirmed veya finalized olmali")
        return cls(
            solana_http_url=os.getenv("SOLANA_HTTP_URL", "https://api.mainnet-beta.solana.com"),
            solana_ws_url=os.getenv("SOLANA_WS_URL", "wss://api.mainnet-beta.solana.com"),
            launch_program_id=os.getenv("LAUNCH_PROGRAM_ID", "").strip() or None,
            database_path=Path(os.getenv("DATABASE_PATH", "data/memecoin_motor.db")),
            commitment=commitment,
            max_backfill_slots=max(0, int(os.getenv("MAX_BACKFILL_SLOTS", "32"))),
            rpc_timeout_seconds=max(1.0, float(os.getenv("RPC_TIMEOUT_SECONDS", "15"))),
            reconnect_max_seconds=max(1.0, float(os.getenv("RECONNECT_MAX_SECONDS", "30"))),
            trade_track_seconds=max(60, int(os.getenv("TRADE_TRACK_SECONDS", "600"))),
            wallet_enrichment_enabled=os.getenv(
                "WALLET_ENRICHMENT_ENABLED", "true"
            ).lower() in {"1", "true", "yes", "on"},
            wallet_early_buyer_limit=max(
                0, int(os.getenv("WALLET_EARLY_BUYER_LIMIT", "3"))
            ),
            wallet_signature_page_size=min(
                1000, max(1, int(os.getenv("WALLET_SIGNATURE_PAGE_SIZE", "100")))
            ),
            wallet_max_signature_pages=max(
                1, int(os.getenv("WALLET_MAX_SIGNATURE_PAGES", "2"))
            ),
            wallet_rpc_interval_seconds=max(
                0.1, float(os.getenv("WALLET_RPC_INTERVAL_SECONDS", "1.0"))
            ),
            paper_enabled=os.getenv("PAPER_ENABLED", "true").lower()
            in {"1", "true", "yes", "on"},
            paper_notional_lamports=max(
                1, int(os.getenv("PAPER_NOTIONAL_LAMPORTS", "100000000"))
            ),
            paper_latency_seconds=max(
                0, int(os.getenv("PAPER_LATENCY_SECONDS", "2"))
            ),
            paper_slippage_bps=max(
                0, int(os.getenv("PAPER_SLIPPAGE_BPS", "300"))
            ),
            paper_base_fee_lamports=max(
                0, int(os.getenv("PAPER_BASE_FEE_LAMPORTS", "5000"))
            ),
            paper_priority_fee_lamports=max(
                0, int(os.getenv("PAPER_PRIORITY_FEE_LAMPORTS", "100000"))
            ),
            paper_jito_tip_lamports=max(
                0, int(os.getenv("PAPER_JITO_TIP_LAMPORTS", "100000"))
            ),
            paper_max_reserve_impact_bps=max(
                1, int(os.getenv("PAPER_MAX_RESERVE_IMPACT_BPS", "1000"))
            ),
            paper_max_fill_wait_seconds=min(
                8, max(5, int(os.getenv("PAPER_MAX_FILL_WAIT_SECONDS", "8")))
            ),
            sniper_enabled=os.getenv("SNIPER_ENABLED", "true").lower()
            in {"1", "true", "yes", "on"},
            sniper_early_buyer_limit=max(
                0, int(os.getenv("SNIPER_EARLY_BUYER_LIMIT", "5"))
            ),
            sniper_max_trade_age_seconds=max(
                1, int(os.getenv("SNIPER_MAX_TRADE_AGE_SECONDS", "10"))
            ),
            sniper_rpc_interval_seconds=max(
                0.2, float(os.getenv("SNIPER_RPC_INTERVAL_SECONDS", "2.0"))
            ),
        )
