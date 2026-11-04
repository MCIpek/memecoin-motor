from memecoin_motor.pump_decoder import base58_encode
from memecoin_motor.transaction_analysis import (
    COMPUTE_BUDGET_PROGRAM, JITO_TIP_ACCOUNTS, analyze_transaction,
)


def test_extracts_fee_payer_priority_fee_jito_tip_and_dont_front():
    limit = 300_000
    price = 2_000_000
    tip_account = next(iter(JITO_TIP_ACCOUNTS))
    transaction = {
        "transaction": {"message": {
            "accountKeys": [
                {"pubkey": "payer", "signer": True},
                {"pubkey": "jitodontfront1111111111111111111111tradewiz"},
            ],
            "instructions": [
                {"programId": COMPUTE_BUDGET_PROGRAM,
                 "data": base58_encode(bytes([2]) + limit.to_bytes(4, "little"))},
                {"programId": COMPUTE_BUDGET_PROGRAM,
                 "data": base58_encode(bytes([3]) + price.to_bytes(8, "little"))},
                {"parsed": {"type": "transfer", "info": {
                    "source": "payer", "destination": tip_account,
                    "lamports": 25_000,
                }}},
            ],
        }},
        "meta": {"fee": 605_000, "computeUnitsConsumed": 100_000},
    }
    result = analyze_transaction(transaction)
    assert result.fee_payer == "payer"
    assert result.compute_unit_limit == limit
    assert result.compute_unit_price_micro_lamports == price
    assert result.estimated_priority_fee_lamports == 600_000
    assert result.jito_tip_lamports == 25_000
    assert result.jito_tip_account == tip_account
    assert result.jitodontfront_present is True


def test_ignores_non_jito_transfer():
    transaction = {
        "transaction": {"message": {"accountKeys": ["payer"], "instructions": [{
            "parsed": {"type": "transfer", "info": {
                "source": "payer", "destination": "someone", "lamports": 99,
            }}
        }]}}, "meta": {},
    }
    result = analyze_transaction(transaction)
    assert result.jito_tip_lamports == 0
    assert result.jito_tip_account is None
