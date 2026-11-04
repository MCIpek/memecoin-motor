from __future__ import annotations

from dataclasses import asdict

from .paper import PaperAssumptions, outcome, simulate_entry, staged_outcome
from .storage import Storage


PAPER_HORIZONS = (60, 300)


def run_paper_cycle(storage: Storage, assumptions: PaperAssumptions,
                    now_timestamp: int, trade_track_seconds: int,
                    recompute_outcomes: bool = False, entry_limit: int = 1000,
                    outcome_limit: int = 2000,
                    live_window_seconds: int | None = None) -> tuple[int, int, int]:
    """V2: bounded fills, reserve execution and unbiased labels for every decision."""
    del trade_track_seconds
    entries = outcomes = labels = 0
    values = asdict(assumptions)
    values["one_way_fee"] = assumptions.one_way_fee
    minimum_cutoff = (
        now_timestamp - live_window_seconds if live_window_seconds is not None else None
    )
    for candidate in storage.v2_entry_candidates(entry_limit, minimum_cutoff):
        cutoff = int(candidate["cutoff_timestamp"])
        earliest = cutoff + assumptions.latency_seconds
        deadline = cutoff + assumptions.max_fill_wait_seconds
        if candidate["quote_asset"] != "SOL":
            storage.save_v2_position(candidate, {"status": "FAILED", "reason": "UNSUPPORTED_QUOTE"},
                                     None, values, False, deadline)
            entries += 1
            continue
        if earliest > deadline:
            storage.save_v2_position(candidate, {"status": "FAILED", "reason": "LATENCY_EXCEEDS_FILL_WINDOW"},
                                     None, values, False, deadline)
            entries += 1
            continue
        trade = storage.first_trade_after(candidate["mint"], earliest, deadline)
        if trade is None:
            if now_timestamp > deadline:
                storage.save_v2_position(candidate, {"status": "FAILED", "reason": "NO_TIMELY_FILL"},
                                         None, values, False, deadline)
                entries += 1
            continue
        result = simulate_entry(trade, assumptions)
        canonical = (candidate["decision"] == "ADAY"
                     and result["status"] == "OPEN"
                     and not storage.has_canonical_v2(candidate["mint"]))
        storage.save_v2_position(candidate, result, trade, values, canonical, deadline)
        entries += 1

    for horizon in PAPER_HORIZONS:
        for position in storage.v2_open_positions(
            now_timestamp, horizon, recompute_outcomes, outcome_limit,
            now_timestamp - horizon - live_window_seconds
            if live_window_seconds is not None else None,
        ):
            start, end = int(position["entry_timestamp"]), int(position["entry_timestamp"]) + horizon
            trades = storage.trades_for_paper_outcome(position["mint"], start, end)
            result = outcome(float(position["entry_price"]), float(position["token_quantity"]),
                             int(position["notional_quote"]), trades, assumptions)
            strategy = staged_outcome(float(position["token_quantity"]),
                                      int(position["notional_quote"]), trades, assumptions)
            if result is None or strategy is None:
                continue
            end_slot = storage.max_trade_slot(position["mint"], start, end)
            quality = "CONTINUOUS"
            if end_slot is None or storage.has_unresolved_gap(int(position["entry_slot"]), end_slot):
                quality = "GAP_AFFECTED"
            storage.save_v2_outcome(position, horizon, result, strategy, quality)
            outcomes += 1
            labels += 1
    storage.commit()
    return entries, outcomes, labels
