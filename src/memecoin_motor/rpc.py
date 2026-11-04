from __future__ import annotations

from itertools import count
from typing import Any

import aiohttp


class RpcError(RuntimeError):
    pass


class SolanaRpc:
    def __init__(self, url: str, timeout_seconds: float):
        self.url = url
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._ids = count(1)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "SolanaRpc":
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._session:
            await self._session.close()

    async def call(self, method: str, params: list[Any]) -> Any:
        if self._session is None:
            raise RuntimeError("SolanaRpc context manager ile kullanilmali")
        payload = {"jsonrpc": "2.0", "id": next(self._ids),
                   "method": method, "params": params}
        async with self._session.post(self.url, json=payload) as response:
            response.raise_for_status()
            body = await response.json()
        if body.get("error"):
            raise RpcError(f"{method}: {body['error']}")
        return body.get("result")

    async def get_transaction(self, signature: str, commitment: str) -> Any:
        commitment = "confirmed" if commitment == "processed" else commitment
        return await self.call("getTransaction", [signature, {
            "commitment": commitment, "encoding": "jsonParsed",
            "maxSupportedTransactionVersion": 1,
        }])

    async def get_signatures_for_address(
        self, address: str, commitment: str, limit: int = 100,
        before: str | None = None,
    ) -> list[dict[str, Any]]:
        commitment = "confirmed" if commitment == "processed" else commitment
        options: dict[str, Any] = {"commitment": commitment, "limit": limit}
        if before:
            options["before"] = before
        return list(await self.call(
            "getSignaturesForAddress", [address, options]
        ) or [])

    async def get_blocks(self, start: int, end: int, commitment: str) -> list[int]:
        commitment = "confirmed" if commitment == "processed" else commitment
        return list(await self.call(
            "getBlocks", [start, end, {"commitment": commitment}]
        ) or [])

    async def get_block(self, slot: int, commitment: str) -> Any:
        commitment = "confirmed" if commitment == "processed" else commitment
        return await self.call("getBlock", [slot, {
            "commitment": commitment, "encoding": "jsonParsed",
            "transactionDetails": "full", "rewards": False,
            "maxSupportedTransactionVersion": 1,
        }])
