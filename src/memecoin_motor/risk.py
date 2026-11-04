from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskFeatures:
    mint: str
    snapshot_age: int
    snapshot_quality: str
    trade_count: int
    unique_buyers: int
    unique_sellers: int
    net_quote_flow: int
    buy_quote_amount: int
    sell_quote_amount: int
    top_buyer_share: float
    top5_buyer_share: float
    creator_sold: bool
    creator_launch_count: int
    creator_sold_token_count: int
    queued_wallets: int
    analyzed_wallets: int
    shared_funder_wallets: int
    max_sniper_score: int
    coordinated_snipers: int
    high_bundle_likelihood_wallets: int


@dataclass(frozen=True, slots=True)
class RiskDecision:
    decision: str
    risk_score: int
    opportunity_score: int
    confidence: float
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]


def evaluate(features: RiskFeatures) -> RiskDecision:
    """Conservative, explainable baseline. It is not an ML prediction."""
    risk = 0
    opportunity = 0
    reasons: list[str] = []
    warnings: list[str] = []
    critical = False

    if features.creator_sold:
        risk += 55
        critical = True
        reasons.append("Creator ilk pencere icinde satis yapti")
    if features.trade_count == 0:
        risk += 25
        reasons.append("Snapshot penceresinde islem yok")
    elif features.trade_count >= 20:
        opportunity += 15
        reasons.append("Islem aktivitesi guclu")

    if features.unique_buyers < 3:
        risk += 18
        reasons.append("Benzersiz alici sayisi cok dusuk")
    elif features.unique_buyers >= 10:
        opportunity += 20
        reasons.append("Benzersiz alici yayilimi olumlu")
    elif features.unique_buyers >= 5:
        opportunity += 10

    if features.net_quote_flow <= 0:
        risk += 25
        reasons.append("Net quote akisi pozitif degil")
    elif features.buy_quote_amount:
        flow_ratio = features.net_quote_flow / features.buy_quote_amount
        if flow_ratio >= 0.7:
            opportunity += 25
            reasons.append("Net alim akisi guclu")
        elif flow_ratio >= 0.35:
            opportunity += 15
        else:
            risk += 8
            warnings.append("Alim akisi satislara gore zayif")

    if features.top_buyer_share >= 0.50:
        risk += 22
        reasons.append("Tek alici alimlarin en az yarisini kontrol ediyor")
    elif features.top_buyer_share >= 0.30:
        risk += 12
        warnings.append("Tek alici yogunlasmasi yuksek")
    elif features.unique_buyers >= 5:
        opportunity += 8

    if features.top5_buyer_share >= 0.90 and features.unique_buyers >= 6:
        risk += 10
        warnings.append("Ilk bes alicida yuksek yogunlasma")

    prior_launches = max(0, features.creator_launch_count - 1)
    if prior_launches >= 2:
        sold_ratio = features.creator_sold_token_count / features.creator_launch_count
        if sold_ratio >= 0.5:
            risk += 15
            reasons.append("Creator gecmisinde erken satis orani yuksek")
        else:
            opportunity += 5
            warnings.append("Creator tekrarlayan launch sahibi")

    if features.shared_funder_wallets >= 2:
        risk += 20
        reasons.append("Birden fazla erken cuzdan ayni fonlayiciya bagli")
    if features.max_sniper_score >= 70:
        risk += 25
        reasons.append("Koordineli sniper skoru kritik")
    elif features.max_sniper_score >= 45:
        risk += 12
        warnings.append("Erken alicilar arasinda sniper adayi var")
    if features.coordinated_snipers >= 2:
        risk += 15
        reasons.append("Birden fazla koordineli sniper tespit edildi")
    if features.high_bundle_likelihood_wallets >= 1:
        risk += 15
        reasons.append("Ayni slot/fee payer kaynakli yuksek bundle ihtimali")

    coverage = (
        features.analyzed_wallets / features.queued_wallets
        if features.queued_wallets else 0.0
    )
    age_confidence = {2: 0.25, 5: 0.38, 10: 0.52, 30: 0.68, 60: 0.78}.get(
        features.snapshot_age, 0.35
    )
    confidence = age_confidence + min(0.15, coverage * 0.15)
    if features.snapshot_quality != "ON_TIME":
        confidence -= 0.20
        warnings.append("Snapshot gec uretildi")
    if coverage < 0.5:
        warnings.append("Cuzdan analizi kapsami dusuk")
    confidence = round(max(0.05, min(0.95, confidence)), 2)

    risk = min(100, risk)
    opportunity = min(100, opportunity)
    if critical or (features.snapshot_age >= 10 and risk >= 65):
        decision = "GIRME"
    elif (
        features.snapshot_age >= 10 and risk <= 35 and opportunity >= 35
        and confidence >= 0.45
    ):
        decision = "ADAY"
    else:
        decision = "IZLE"
    return RiskDecision(
        decision, risk, opportunity, confidence, tuple(reasons), tuple(warnings)
    )
