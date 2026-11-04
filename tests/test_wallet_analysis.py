from memecoin_motor.wallet_analysis import inbound_system_transfers


def test_finds_outer_and_inner_native_sol_transfers():
    transaction = {
        "blockTime": 123,
        "transaction": {"message": {"instructions": [{
            "parsed": {"type": "transfer", "info": {
                "source": "funder", "destination": "wallet", "lamports": 9
            }}
        }]}},
        "meta": {"innerInstructions": [{"instructions": [{
            "parsed": {"type": "transfer", "info": {
                "source": "other", "destination": "wallet", "lamports": 4
            }}
        }, {
            "parsed": {"type": "transfer", "info": {
                "source": "wallet", "destination": "elsewhere", "lamports": 3
            }}
        }]}]},
    }
    found = inbound_system_transfers(transaction, "wallet", "sig")
    assert [(item.source, item.lamports) for item in found] == [
        ("funder", 9), ("other", 4)
    ]
    assert all(item.signature == "sig" and item.block_time == 123 for item in found)


def test_ignores_partially_parsed_and_malformed_instructions():
    transaction = {
        "transaction": {"message": {"instructions": ["raw", {"parsed": "raw"}]}},
        "meta": {"innerInstructions": ["raw", {"instructions": [None]}]},
    }
    assert inbound_system_transfers(transaction, "wallet", "sig") == []
