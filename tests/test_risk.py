from memecoin_motor.risk import RiskFeatures, evaluate


def features(**overrides):
    values = dict(
        mint="mint", snapshot_age=30, snapshot_quality="ON_TIME",
        trade_count=30, unique_buyers=15, unique_sellers=2,
        net_quote_flow=80, buy_quote_amount=100, sell_quote_amount=20,
        top_buyer_share=0.15, top5_buyer_share=0.55,
        creator_sold=False, creator_launch_count=1,
        creator_sold_token_count=0, queued_wallets=4, analyzed_wallets=3,
        shared_funder_wallets=0,
        max_sniper_score=0, coordinated_snipers=0,
        high_bundle_likelihood_wallets=0,
    )
    values.update(overrides)
    return RiskFeatures(**values)


def test_good_flow_becomes_candidate_only_with_enough_age_and_confidence():
    result = evaluate(features())
    assert result.decision == "ADAY"
    assert result.risk_score <= 35
    assert result.confidence >= 0.45
    early = evaluate(features(snapshot_age=2))
    assert early.decision == "IZLE"


def test_creator_sell_is_hard_rejection():
    result = evaluate(features(creator_sold=True))
    assert result.decision == "GIRME"
    assert result.risk_score >= 55


def test_shared_funder_and_concentration_raise_risk():
    result = evaluate(features(
        unique_buyers=2, net_quote_flow=-1, top_buyer_share=0.8,
        top5_buyer_share=1.0, shared_funder_wallets=2,
    ))
    assert result.decision == "GIRME"
    assert result.risk_score >= 65


def test_late_snapshot_reduces_confidence():
    on_time = evaluate(features())
    late = evaluate(features(snapshot_quality="LATE"))
    assert late.confidence < on_time.confidence
    assert "Snapshot gec uretildi" in late.warnings


def test_missing_early_data_is_watch_not_rejection():
    result = evaluate(features(
        snapshot_age=5, trade_count=0, unique_buyers=0,
        net_quote_flow=0, buy_quote_amount=0, sell_quote_amount=0,
    ))
    assert result.risk_score >= 65
    assert result.decision == "IZLE"


def test_coordinated_sniper_bundle_raises_risk():
    result = evaluate(features(
        max_sniper_score=85, coordinated_snipers=2,
        high_bundle_likelihood_wallets=1,
    ))
    assert result.risk_score >= 55
    assert any("sniper" in reason.lower() for reason in result.reasons)
