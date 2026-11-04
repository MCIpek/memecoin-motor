from memecoin_motor.parser import (
    extract_creator,
    extract_token_mints,
    is_pump_creation_logs,
)


def test_extracts_creator_and_unique_mints():
    result = {
        "transaction": {"message": {"accountKeys": [
            {"pubkey": "creator", "signer": True}, "program"
        ]}},
        "meta": {
            "preTokenBalances": [{"mint": "mint-a"}],
            "postTokenBalances": [{"mint": "mint-a"}, {"mint": "mint-b"}],
        },
    }
    assert extract_creator(result) == "creator"
    assert extract_token_mints(result) == {"mint-a", "mint-b"}


def test_detects_only_pump_creation_instruction_logs():
    assert is_pump_creation_logs(["Program log: Instruction: Create"])
    assert is_pump_creation_logs(["Program log: Instruction: CreateV2"])
    assert not is_pump_creation_logs(["Program log: Instruction: Buy"])
    assert not is_pump_creation_logs(["Program log: Instruction: Sell"])
    assert not is_pump_creation_logs([
        "Program log: Instruction: MigrateV2",
        "Program log: Instruction: CreateIdempotent",
    ])
