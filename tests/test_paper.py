from memecoin_motor.paper import (
    PaperAssumptions, market_outcome, outcome, simulate_entry,
)


def assumptions(**changes):
    values = dict(
        notional_quote=100_000_000, latency_seconds=2, slippage_bps=300,
        base_fee=5_000, priority_fee=100_000, jito_tip=100_000,
        max_reserve_impact_bps=1_000,
    )
    values.update(changes)
    return PaperAssumptions(**values)


def trade(price_quote=100, reserve=2_000_000_000, token_reserve=20_000_000_000):
    return {
        "token_amount": 1_000_000, "quote_amount": price_quote * 1_000_000,
        "virtual_quote_reserves": reserve,
        "virtual_token_reserves": token_reserve, "fee": 0,
        "event_timestamp": 1, "user_address": "wallet", "is_buy": 1,
    }


def test_entry_deducts_fees_slippage_and_estimates_impact():
    result = simulate_entry(trade(), assumptions())
    assert result["status"] == "OPEN"
    assert result["entry_price"] > 0
    assert result["entry_fee"] == 205_000
    assert result["estimated_impact_bps"] == 500


def test_entry_fails_when_notional_is_too_large_for_reserve():
    result = simulate_entry(trade(reserve=100_000_000), assumptions())
    assert result == {"status": "FAILED", "reason": "RESERVE_IMPACT_LIMIT"}


def test_outcome_reports_net_multiples_after_exit_costs():
    entry = simulate_entry(trade(), assumptions())
    result = outcome(
        entry["entry_price"], entry["token_quantity"], 100_000_000,
        [trade(100, 2_000_000_000, 20_000_000_000),
         trade(200, 4_000_000_000, 10_000_000_000),
         trade(50, 1_000_000_000, 30_000_000_000)], assumptions(),
    )
    assert result is not None
    assert result["sample_count"] == 3
    assert result["max_x"] > result["min_x"]
    assert result["final_x"] >= 0


def test_market_outcome_labels_raw_price_path_without_selection():
    result = market_outcome(trade(100), [trade(80), trade(250), trade(120)])
    assert result is not None
    assert result["max_market_x"] == 2.5
    assert result["min_market_x"] == 0.8
    assert result["final_market_x"] == 1.2
    assert result["hit_2x"] is True
