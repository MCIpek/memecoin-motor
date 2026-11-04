from __future__ import annotations

from dataclasses import asdict

from .risk import RiskFeatures, evaluate
from .storage import Storage


RULESET_VERSION = "baseline-v1"


def score_snapshots(
    storage: Storage, mint: str | None = None, only_unscored: bool = False,
) -> int:
    count = 0
    for row in storage.risk_feature_rows(mint, only_unscored):
        features = RiskFeatures(
            mint=row["mint"], snapshot_age=int(row["target_age_seconds"]),
            snapshot_quality=row["snapshot_quality"],
            trade_count=int(row["trade_count"]),
            unique_buyers=int(row["unique_buyers"]),
            unique_sellers=int(row["unique_sellers"]),
            net_quote_flow=int(row["net_quote_flow"]),
            buy_quote_amount=int(row["buy_quote_amount"]),
            sell_quote_amount=int(row["sell_quote_amount"]),
            top_buyer_share=float(row["top_buyer_share"]),
            top5_buyer_share=float(row["top5_buyer_share"]),
            creator_sold=bool(row["creator_sold"]),
            creator_launch_count=int(row["creator_launch_count"]),
            creator_sold_token_count=int(row["creator_sold_token_count"]),
            queued_wallets=int(row["queued_wallets"]),
            analyzed_wallets=int(row["analyzed_wallets"]),
            shared_funder_wallets=int(row["shared_funder_wallets"]),
            max_sniper_score=int(row["max_sniper_score"]),
            coordinated_snipers=int(row["coordinated_snipers"]),
            high_bundle_likelihood_wallets=int(
                row["high_bundle_likelihood_wallets"]
            ),
        )
        result = evaluate(features)
        storage.save_risk_decision(
            features.mint, features.snapshot_age, RULESET_VERSION,
            result.decision, result.risk_score, result.opportunity_score,
            result.confidence, result.reasons, result.warnings, asdict(features),
        )
        count += 1
    return count
