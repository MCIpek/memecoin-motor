from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .pump_decoder import base58_decode


COMPUTE_BUDGET_PROGRAM = "ComputeBudget111111111111111111111111111111"
JITO_TIP_ACCOUNTS = frozenset({
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
})


@dataclass(frozen=True, slots=True)
class TransactionEvidence:
    fee_payer: str | None
    transaction_fee_lamports: int | None
    compute_units_consumed: int | None
    compute_unit_limit: int | None
    compute_unit_price_micro_lamports: int | None
    estimated_priority_fee_lamports: int | None
    jito_tip_lamports: int
    jito_tip_account: str | None
    jitodontfront_present: bool


def _account_pubkey(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        pubkey = value.get("pubkey")
        return pubkey if isinstance(pubkey, str) else None
    return None


def _all_instructions(transaction: dict[str, Any]) -> Iterable[dict[str, Any]]:
    envelope = transaction.get("transaction") or {}
    message = envelope.get("message") if isinstance(envelope, dict) else None
    if isinstance(message, dict):
        for instruction in message.get("instructions") or []:
            if isinstance(instruction, dict):
                yield instruction
    meta = transaction.get("meta") or {}
    if isinstance(meta, dict):
        for group in meta.get("innerInstructions") or []:
            if not isinstance(group, dict):
                continue
            for instruction in group.get("instructions") or []:
                if isinstance(instruction, dict):
                    yield instruction


def analyze_transaction(transaction: dict[str, Any]) -> TransactionEvidence:
    envelope = transaction.get("transaction") or {}
    message = envelope.get("message") if isinstance(envelope, dict) else None
    keys = message.get("accountKeys") or [] if isinstance(message, dict) else []
    pubkeys = [key for value in keys if (key := _account_pubkey(value))]
    fee_payer = pubkeys[0] if pubkeys else None
    cu_limit: int | None = None
    cu_price: int | None = None
    jito_tip = 0
    jito_account: str | None = None
    for instruction in _all_instructions(transaction):
        program_id = instruction.get("programId")
        if program_id == COMPUTE_BUDGET_PROGRAM and isinstance(
            instruction.get("data"), str
        ):
            try:
                raw = base58_decode(instruction["data"])
            except Exception:
                raw = b""
            if len(raw) >= 5 and raw[0] == 2:
                cu_limit = int.from_bytes(raw[1:5], "little")
            elif len(raw) >= 9 and raw[0] == 3:
                cu_price = int.from_bytes(raw[1:9], "little")
        parsed = instruction.get("parsed") or {}
        info = parsed.get("info") or {} if isinstance(parsed, dict) else {}
        if not isinstance(info, dict) or parsed.get("type") not in {
            "transfer", "transferWithSeed"
        }:
            continue
        destination = info.get("destination")
        lamports = info.get("lamports")
        if destination in JITO_TIP_ACCOUNTS and lamports:
            jito_tip += int(lamports)
            jito_account = destination
    meta = transaction.get("meta") or {}
    fee = meta.get("fee") if isinstance(meta, dict) else None
    consumed = meta.get("computeUnitsConsumed") if isinstance(meta, dict) else None
    priority = None
    if cu_limit is not None and cu_price is not None:
        priority = (cu_limit * cu_price + 999_999) // 1_000_000
    config = message.get("transactionConfig") if isinstance(message, dict) else None
    if isinstance(config, dict) and config.get("priorityFee") is not None:
        priority = int(config["priorityFee"])
    return TransactionEvidence(
        fee_payer, int(fee) if fee is not None else None,
        int(consumed) if consumed is not None else None, cu_limit, cu_price,
        priority, jito_tip, jito_account,
        any(value.startswith("jitodontfront") for value in pubkeys),
    )
