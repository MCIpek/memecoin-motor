from __future__ import annotations

from typing import Any

from .storage import Storage


def score_snipers(storage: Storage, mint: str) -> int:
    saved = 0
    for row in storage.sniper_feature_rows(mint):
        age = int(row["first_buy_age_seconds"])
        same_slot = int(row["same_slot_early_buyers"] or 0)
        repeated = int(row["repeated_early_launches"] or 0)
        quick_sell = row["quick_sell_seconds"]
        funder_peers = max(0, int(row["same_funder_peers"] or 0))
        fee_payer_peers = max(0, int(row["same_fee_payer_peers"] or 0))
        tip = int(row["jito_tip_lamports"] or 0)
        priority_fee = row["priority_fee_lamports"]
        score = 0
        reasons: list[str] = []
        if age <= 2:
            score += 25
            reasons.append("Launch sonrasi ilk 2 saniyede alim")
        elif age <= 5:
            score += 15
            reasons.append("Launch sonrasi ilk 5 saniyede alim")
        if same_slot >= 3:
            score += 20
            reasons.append(f"Ayni slotta {same_slot} erken alici")
        elif same_slot == 2:
            score += 10
            reasons.append("Ayni slotta iki erken alici")
        if repeated >= 10:
            score += 20
            reasons.append(f"{repeated} launchta tekrar erken giris")
        elif repeated >= 3:
            score += 10
            reasons.append(f"{repeated} launchta tekrar erken giris")
        if quick_sell is not None and 0 <= int(quick_sell) <= 30:
            score += 15
            reasons.append(f"{int(quick_sell)} saniyede hizli satis")
        if funder_peers >= 2:
            score += 20
            reasons.append(f"Ayni fonlayiciya bagli {funder_peers} peer")
        if fee_payer_peers >= 1:
            score += 25
            reasons.append(f"Ayni fee payer kullanan {fee_payer_peers} peer")
        if tip > 0:
            score += 10
            reasons.append(f"Jito tip izi: {tip} lamport")
        if priority_fee is not None and int(priority_fee) >= 100_000:
            score += 8
            reasons.append(f"Yuksek priority fee: {int(priority_fee)} lamport")
        if bool(row["jitodontfront_present"]):
            score += 5
            reasons.append("jitodontfront hesabi mevcut")
        score = min(100, score)
        if score >= 70:
            classification = "COORDINATED_SNIPER"
        elif score >= 45:
            classification = "SNIPER_CANDIDATE"
        else:
            classification = "EARLY_TRADER"
        if fee_payer_peers >= 1 and same_slot >= 2:
            bundle = "HIGH"
        elif tip > 0 or (funder_peers >= 2 and same_slot >= 2):
            bundle = "MEDIUM"
        else:
            bundle = "LOW"
        evidence_parts = int(bool(row["transaction_analyzed"])) + int(
            bool(row["wallet_analyzed"])
        )
        confidence = round(min(0.95, 0.35 + evidence_parts * 0.25), 2)
        values: dict[str, Any] = dict(row)
        values.update({
            "score": score, "classification": classification,
            "confidence": confidence, "same_funder_peers": funder_peers,
            "same_fee_payer_peers": fee_payer_peers,
            "jito_routed": tip > 0, "jito_tip_lamports": tip,
            "priority_fee_lamports": priority_fee,
            "bundle_likelihood": bundle, "reasons": reasons,
        })
        storage.save_sniper_score(values)
        saved += 1
    return saved
