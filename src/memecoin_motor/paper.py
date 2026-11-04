from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class PaperAssumptions:
    notional_quote: int
    latency_seconds: int
    slippage_bps: int
    base_fee: int
    priority_fee: int
    jito_tip: int
    max_reserve_impact_bps: int
    max_fill_wait_seconds: int = 8

    @property
    def one_way_fee(self) -> int:
        return self.base_fee + self.priority_fee + self.jito_tip


def unit_price(trade: Any) -> float | None:
    token_amount, quote_amount = int(trade["token_amount"]), int(trade["quote_amount"])
    return quote_amount / token_amount if token_amount > 0 and quote_amount > 0 else None


def _reserves(row: Any) -> tuple[int, int]:
    return int(row["virtual_quote_reserves"]), int(row["virtual_token_reserves"])


def _value(row: Any, key: str, default: int = 0) -> int:
    try:
        return int(row[key])
    except (KeyError, IndexError, TypeError):
        return default


def _protocol_fee_bps(row: Any) -> int:
    return min(1_000, max(0, round(_value(row, "fee") / max(1, _value(row, "quote_amount")) * 10_000)))


def executable_buy(row: Any, quote_budget: int, assumptions: PaperAssumptions) -> dict[str, Any]:
    quote_reserve, token_reserve = _reserves(row)
    spend = quote_budget - assumptions.one_way_fee
    if spend <= 0 or quote_reserve <= 0 or token_reserve <= 0:
        return {"status": "FAILED", "reason": "INVALID_RESERVES_OR_NOTIONAL"}
    impact_bps = round(quote_budget / quote_reserve * 10_000)
    if impact_bps > assumptions.max_reserve_impact_bps:
        return {"status": "FAILED", "reason": "RESERVE_IMPACT_LIMIT"}
    protocol_fee_bps = _protocol_fee_bps(row)
    curve_input = spend * (10_000 - protocol_fee_bps) / 10_000
    tokens = token_reserve * curve_input / (quote_reserve + curve_input)
    tokens *= (10_000 - assumptions.slippage_bps) / 10_000
    if tokens <= 0:
        return {"status": "FAILED", "reason": "ZERO_EXECUTABLE_OUTPUT"}
    return {
        "status": "OPEN", "reason": None, "entry_price": quote_budget / tokens,
        "token_quantity": tokens, "entry_fee": assumptions.one_way_fee,
        "protocol_fee_bps": protocol_fee_bps, "estimated_impact_bps": impact_bps,
        "entry_quote_reserve": quote_reserve, "entry_token_reserve": token_reserve,
    }


def simulate_entry(trade: Any, assumptions: PaperAssumptions) -> dict[str, Any]:
    return executable_buy(trade, assumptions.notional_quote, assumptions)


def executable_sell(row: Any, token_quantity: float, assumptions: PaperAssumptions) -> float:
    quote_reserve, token_reserve = _reserves(row)
    if token_quantity <= 0 or quote_reserve <= 0 or token_reserve <= 0:
        return 0.0
    gross = quote_reserve * token_quantity / (token_reserve + token_quantity)
    gross *= (10_000 - _protocol_fee_bps(row)) / 10_000
    gross *= (10_000 - assumptions.slippage_bps) / 10_000
    return max(0.0, gross - assumptions.one_way_fee)


def outcome(entry_price: float, token_quantity: float, entry_cost: int,
            trades: Sequence[Any], assumptions: PaperAssumptions) -> dict[str, Any] | None:
    del entry_price
    multiples = [executable_sell(row, token_quantity, assumptions) / entry_cost for row in trades]
    if not multiples:
        return None
    peak, max_drawdown = 1.0, 0.0
    for value in multiples:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, (peak - value) / peak * 100)
    maximum = max(multiples)
    return {"sample_count": len(multiples), "max_x": maximum,
            "min_x": min(multiples), "final_x": multiples[-1],
            "max_drawdown_pct": max_drawdown, "hit_1_5x": maximum >= 1.5,
            "hit_2x": maximum >= 2.0, "hit_3x": maximum >= 3.0,
            "hit_5x": maximum >= 5.0}


def staged_outcome(token_quantity: float, entry_cost: int, trades: Sequence[Any],
                   assumptions: PaperAssumptions) -> dict[str, Any] | None:
    """40% at 1.5x, 30% at 2x, 20% at 3x; runner exits on momentum break/end."""
    if not trades:
        return None
    remaining, cash, next_target, peak_x = token_quantity, 0.0, 0, 0.0
    tranches: list[dict[str, Any]] = []
    targets = ((1.5, .40), (2.0, .30), (3.0, .20))
    exit_reason = "HORIZON"
    for index, row in enumerate(trades):
        full_x = executable_sell(row, token_quantity, assumptions) / entry_cost
        peak_x = max(peak_x, full_x)
        while next_target < len(targets) and full_x >= targets[next_target][0]:
            target, fraction = targets[next_target]
            qty = token_quantity * fraction
            proceeds = executable_sell(row, qty, assumptions)
            cash, remaining = cash + proceeds, remaining - qty
            tranches.append({"target_x": target, "fraction": fraction,
                              "timestamp": int(row["event_timestamp"]), "proceeds": proceeds})
            next_target += 1
        window_start = int(row["event_timestamp"]) - 15
        window = [x for x in trades[max(0, index - 100):index + 1]
                  if int(x["event_timestamp"]) >= window_start]
        buyers = len({x["user_address"] for x in window if _value(x, "is_buy") == 1})
        sellers = len({x["user_address"] for x in window if _value(x, "is_buy") == 0})
        flow = sum((1 if _value(x, "is_buy") else -1) * _value(x, "quote_amount") for x in window)
        if remaining > 0 and peak_x >= 1 and (buyers + 1) / (sellers + 1) < .8 \
                and flow < 0 and full_x <= peak_x * .85:
            proceeds = executable_sell(row, remaining, assumptions)
            cash += proceeds
            tranches.append({"target_x": None, "fraction": remaining / token_quantity,
                              "timestamp": int(row["event_timestamp"]), "proceeds": proceeds,
                              "trigger": "MOMENTUM_BREAK"})
            remaining, exit_reason = 0, "MOMENTUM_BREAK"
            break
    if remaining > 0:
        cash += executable_sell(trades[-1], remaining, assumptions)
    return {"strategy_x": cash / entry_cost, "exit_reason": exit_reason,
            "tranches": tranches, "remaining_fraction": remaining / token_quantity}


def market_outcome(reference: Any, trades: Sequence[Any]) -> dict[str, Any] | None:
    reference_price = unit_price(reference)
    prices = [price for row in trades if (price := unit_price(row)) is not None]
    if reference_price is None or not prices:
        return None
    multiples, maximum = [price / reference_price for price in prices], 0.0
    maximum = max(multiples)
    return {"sample_count": len(multiples), "max_market_x": maximum,
            "min_market_x": min(multiples), "final_market_x": multiples[-1],
            "hit_1_5x": maximum >= 1.5, "hit_2x": maximum >= 2.0,
            "hit_3x": maximum >= 3.0, "hit_5x": maximum >= 5.0}
