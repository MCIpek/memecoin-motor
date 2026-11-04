from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True, slots=True)
class ChainEvent:
    signature: str
    slot: int
    program_id: str
    commitment: str
    client_received_at: str
    processed_at: str
    provider_name: str
    block_time: int | None = None
    tx_index_in_block: int | None = None
    ingestion_latency_ms: int | None = None
    is_backfilled: bool = False
    stream_gap_detected: bool = False
    data_completeness: str = "PARTIAL"
    transaction_error: str | None = None
    logs: tuple[str, ...] = ()
    raw_transaction: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TokenObservation:
    mint: str
    creator: str | None
    program_id: str
    launch_slot: int
    block_time: int | None
    first_signature: str
    first_seen_at: str
    data_completeness: str


@dataclass(frozen=True, slots=True)
class SlotGap:
    start_slot: int
    end_slot: int
    detected_at: str
    provider_name: str
    status: str = "DETECTED"
    detail: str | None = None
