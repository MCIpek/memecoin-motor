from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class FundingTransfer:
    source: str
    destination: str
    lamports: int
    signature: str
    block_time: int | None


def _instructions(transaction: dict[str, Any]) -> Iterable[dict[str, Any]]:
    envelope = transaction.get("transaction") or {}
    if not isinstance(envelope, dict):
        return
    message = envelope.get("message") or {}
    if not isinstance(message, dict):
        return
    for instruction in message.get("instructions") or []:
        if isinstance(instruction, dict):
            yield instruction
    meta = transaction.get("meta") or {}
    if not isinstance(meta, dict):
        return
    for group in meta.get("innerInstructions") or []:
        if not isinstance(group, dict):
            continue
        for instruction in group.get("instructions") or []:
            if isinstance(instruction, dict):
                yield instruction


def inbound_system_transfers(
    transaction: dict[str, Any], wallet: str, signature: str,
) -> list[FundingTransfer]:
    """Return explicit jsonParsed native-SOL transfers into wallet.

    Balance deltas are deliberately not guessed because fees and account creation
    can make the apparent source ambiguous.
    """
    found: list[FundingTransfer] = []
    for instruction in _instructions(transaction):
        parsed = instruction.get("parsed") or {}
        if not isinstance(parsed, dict):
            continue
        info = parsed.get("info") or {}
        if not isinstance(info, dict):
            continue
        if parsed.get("type") not in {"transfer", "transferWithSeed"}:
            continue
        source = info.get("source")
        destination = info.get("destination")
        lamports = info.get("lamports")
        if destination != wallet or not source or source == wallet or not lamports:
            continue
        found.append(FundingTransfer(
            source=source, destination=destination, lamports=int(lamports),
            signature=signature, block_time=transaction.get("blockTime"),
        ))
    return found
