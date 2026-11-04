from memecoin_motor.sniper import score_snipers


class FakeStorage:
    def __init__(self):
        self.saved = []

    def sniper_feature_rows(self, mint):
        return [{
            "mint": mint, "user_address": "wallet",
            "first_buy_age_seconds": 1, "same_slot_early_buyers": 4,
            "repeated_early_launches": 15, "quick_sell_seconds": 12,
            "same_funder_peers": 2, "same_fee_payer_peers": 1,
            "jito_tip_lamports": 10_000, "priority_fee_lamports": 200_000,
            "transaction_analyzed": 1, "wallet_analyzed": 1,
            "jitodontfront_present": 0,
        }]

    def save_sniper_score(self, values):
        self.saved.append(values)


def test_scores_coordinated_sniper_and_high_bundle_likelihood():
    storage = FakeStorage()
    assert score_snipers(storage, "mint") == 1
    result = storage.saved[0]
    assert result["classification"] == "COORDINATED_SNIPER"
    assert result["bundle_likelihood"] == "HIGH"
    assert result["jito_routed"] is True
    assert result["confidence"] == 0.85
