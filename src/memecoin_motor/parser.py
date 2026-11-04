from __future__ import annotations

from typing import Any


PUMP_CREATE_LOG_MARKERS = (
    "instruction: create",
    "instruction: create_v2",
    "instruction: createv2",
)


def is_pump_creation_logs(logs: list[str] | tuple[str, ...]) -> bool:
    """Pump create islemlerini buy/sell trafiginden erken ayirir."""
    normalized = {line.casefold().strip() for line in logs}
    return any(
        f"program log: {marker}" in normalized
        for marker in PUMP_CREATE_LOG_MARKERS
    )


def _account_key(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("pubkey"), str):
        return value["pubkey"]
    return None


def extract_creator(result: dict[str, Any]) -> str | None:
    message = ((result.get("transaction") or {}).get("message") or {})
    keys = message.get("accountKeys") or []
    return _account_key(keys[0]) if keys else None


def extract_token_mints(result: dict[str, Any]) -> set[str]:
    """Launch-specific decoder eklenene kadar islemde gozlenen mintleri bulur."""
    meta = result.get("meta") or {}
    mints: set[str] = set()
    for field in ("preTokenBalances", "postTokenBalances"):
        for balance in meta.get(field) or []:
            mint = balance.get("mint") if isinstance(balance, dict) else None
            if isinstance(mint, str) and mint:
                mints.add(mint)
    return mints


def transaction_mentions_program(result: dict[str, Any], program_id: str) -> bool:
    message = ((result.get("transaction") or {}).get("message") or {})
    keys = {_account_key(value) for value in message.get("accountKeys") or []}
    return program_id in keys
