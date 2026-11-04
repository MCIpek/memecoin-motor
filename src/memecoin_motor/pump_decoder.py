from __future__ import annotations

import json
import base64
import struct
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

PUMP_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class PumpDecodeError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PumpLaunch:
    instruction_name: str
    name: str
    symbol: str
    uri: str
    mint: str
    bonding_curve: str
    user: str
    creator: str
    timestamp: int
    virtual_token_reserves: int
    virtual_sol_reserves: int
    real_token_reserves: int
    token_total_supply: int
    token_program: str
    is_mayhem_mode: bool
    is_cashback_enabled: bool
    quote_mint: str
    virtual_quote_reserves: int

    @property
    def quote_asset(self) -> str:
        if self.quote_mint == "11111111111111111111111111111111":
            return "SOL"
        return self.quote_mint


@dataclass(frozen=True, slots=True)
class PumpShareholder:
    address: str
    share_bps: int


@dataclass(frozen=True, slots=True)
class PumpTrade:
    event_index: int
    mint: str
    sol_amount: int
    token_amount: int
    is_buy: bool
    user: str
    timestamp: int
    virtual_sol_reserves: int
    virtual_token_reserves: int
    real_sol_reserves: int
    real_token_reserves: int
    fee_recipient: str
    fee_basis_points: int
    fee: int
    creator: str
    creator_fee_basis_points: int
    creator_fee: int
    track_volume: bool
    total_unclaimed_tokens: int
    total_claimed_tokens: int
    current_sol_volume: int
    last_update_timestamp: int
    ix_name: str
    mayhem_mode: bool
    cashback_fee_basis_points: int
    cashback: int
    buyback_fee_basis_points: int
    buyback_fee: int
    shareholders: tuple[PumpShareholder, ...]
    quote_mint: str
    quote_amount: int
    virtual_quote_reserves: int
    real_quote_reserves: int

    @property
    def effective_quote_amount(self) -> int:
        return self.quote_amount or self.sol_amount

    @property
    def quote_asset(self) -> str:
        if self.quote_mint == "11111111111111111111111111111111":
            return "SOL"
        return self.quote_mint


def base58_decode(value: str) -> bytes:
    number = 0
    try:
        for char in value:
            number = number * 58 + BASE58_ALPHABET.index(char)
    except ValueError as exc:
        raise PumpDecodeError("gecersiz base58 veri") from exc
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    return b"\x00" * (len(value) - len(value.lstrip("1"))) + raw


def base58_encode(value: bytes) -> str:
    zeroes = len(value) - len(value.lstrip(b"\x00"))
    number = int.from_bytes(value, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded
    return "1" * zeroes + encoded


class _Cursor:
    def __init__(self, data: bytes, named_types: dict[str, list[dict[str, Any]]] | None = None):
        self.data = data
        self.offset = 0
        self.named_types = named_types or {}

    def read(self, size: int) -> bytes:
        end = self.offset + size
        if end > len(self.data):
            raise PumpDecodeError("borsh verisi beklenenden kisa")
        value = self.data[self.offset:end]
        self.offset = end
        return value

    def decode(self, kind: Any) -> Any:
        if isinstance(kind, dict) and "vec" in kind:
            size = struct.unpack("<I", self.read(4))[0]
            return [self.decode(kind["vec"]) for _ in range(size)]
        if isinstance(kind, dict) and "defined" in kind:
            name = kind["defined"]["name"]
            fields = self.named_types.get(name)
            if fields is None:
                raise PumpDecodeError(f"IDL tipi bulunamadi: {name}")
            return {field["name"]: self.decode(field["type"]) for field in fields}
        if kind == "string":
            size = struct.unpack("<I", self.read(4))[0]
            return self.read(size).decode("utf-8")
        if kind == "pubkey":
            return base58_encode(self.read(32))
        if kind == "bool":
            value = self.read(1)[0]
            if value not in (0, 1):
                raise PumpDecodeError("gecersiz bool")
            return bool(value)
        formats = {"u8": "<B", "u16": "<H", "u32": "<I", "u64": "<Q",
                   "i8": "<b", "i16": "<h", "i32": "<i", "i64": "<q"}
        if kind in formats:
            fmt = formats[kind]
            return struct.unpack(fmt, self.read(struct.calcsize(fmt)))[0]
        raise PumpDecodeError(f"desteklenmeyen IDL tipi: {kind!r}")


@lru_cache(maxsize=1)
def load_pump_idl() -> dict[str, Any]:
    resource = files("memecoin_motor.resources").joinpath("pump.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def _discriminator(value: list[int]) -> bytes:
    return bytes(value)


def _instruction_name(transaction_result: dict[str, Any], idl: dict[str, Any]) -> str | None:
    wanted = {
        _discriminator(item["discriminator"]): item["name"]
        for item in idl["instructions"]
        if item["name"] in {"create", "create_v2"}
    }
    message = ((transaction_result.get("transaction") or {}).get("message") or {})
    for instruction in message.get("instructions") or []:
        if instruction.get("programId") != PUMP_PROGRAM_ID or not instruction.get("data"):
            continue
        raw = base58_decode(instruction["data"])
        name = wanted.get(raw[:8])
        if name:
            return name
    return None


def _create_event_schema(idl: dict[str, Any]) -> tuple[bytes, list[dict[str, Any]]]:
    event = next(item for item in idl["events"] if item["name"] == "CreateEvent")
    event_type = next(item for item in idl["types"] if item["name"] == "CreateEvent")
    return _discriminator(event["discriminator"]), event_type["type"]["fields"]


def _named_types(idl: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        item["name"]: item["type"].get("fields", [])
        for item in idl.get("types", [])
        if item.get("type", {}).get("kind") == "struct"
    }


def _event_payloads(transaction_result: dict[str, Any]) -> list[bytes]:
    payloads: list[bytes] = []
    meta = transaction_result.get("meta") or {}
    for group in meta.get("innerInstructions") or []:
        for instruction in group.get("instructions") or []:
            if instruction.get("programId") == PUMP_PROGRAM_ID and instruction.get("data"):
                payloads.append(base58_decode(instruction["data"]))
    return payloads


def decode_pump_launch(transaction_result: dict[str, Any]) -> PumpLaunch | None:
    """Resmi IDL discriminator ve CreateEvent semasiyla Pump launch decode eder."""
    idl = load_pump_idl()
    instruction_name = _instruction_name(transaction_result, idl)
    if instruction_name is None:
        return None
    event_discriminator, fields = _create_event_schema(idl)
    for raw in _event_payloads(transaction_result):
        if raw[:8] == event_discriminator:
            body = raw[8:]
        elif raw[8:16] == event_discriminator:  # Anchor event-CPI prefix
            body = raw[16:]
        else:
            continue
        cursor = _Cursor(body, _named_types(idl))
        decoded = {field["name"]: cursor.decode(field["type"]) for field in fields}
        return PumpLaunch(instruction_name=instruction_name, **decoded)
    raise PumpDecodeError(f"{instruction_name} bulundu fakat CreateEvent bulunamadi")


def decode_pump_trade_logs(logs: list[str] | tuple[str, ...]) -> list[PumpTrade]:
    """WebSocket loglarindaki Anchor TradeEvent verilerini RPC cagirmadan cozer."""
    idl = load_pump_idl()
    event = next(item for item in idl["events"] if item["name"] == "TradeEvent")
    discriminator = _discriminator(event["discriminator"])
    fields = _named_types(idl)["TradeEvent"]
    trades: list[PumpTrade] = []
    for line in logs:
        if not line.startswith("Program data: "):
            continue
        try:
            raw = base64.b64decode(line.removeprefix("Program data: "), validate=True)
        except (ValueError, base64.binascii.Error):
            continue
        if raw[:8] != discriminator:
            continue
        cursor = _Cursor(raw[8:], _named_types(idl))
        decoded = {field["name"]: cursor.decode(field["type"]) for field in fields}
        decoded["shareholders"] = tuple(
            PumpShareholder(**item) for item in decoded["shareholders"]
        )
        trades.append(PumpTrade(event_index=len(trades), **decoded))
    return trades
