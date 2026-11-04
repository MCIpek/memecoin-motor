import json
from pathlib import Path

from memecoin_motor.pump_decoder import (
    PUMP_PROGRAM_ID,
    base58_decode,
    base58_encode,
    decode_pump_launch,
    decode_pump_trade_logs,
    load_pump_idl,
)


def test_vendored_idl_matches_program():
    assert load_pump_idl()["address"] == PUMP_PROGRAM_ID


def test_base58_round_trip():
    value = bytes(range(32))
    assert base58_decode(base58_encode(value)) == value


def test_decodes_real_create_v2_fixture():
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "pump_create_v2.json").read_text("utf-8")
    )
    launch = decode_pump_launch(fixture)
    assert launch is not None
    assert launch.instruction_name == "create_v2"
    assert launch.name == "ARROW"
    assert launch.symbol == "ARROW"
    assert launch.mint == "8JvquttxdYiGmUYn5zoc7tcEwtZVB74uXQ4LkQV6pump"
    assert launch.bonding_curve == "1dvFFeHLR7gWsqwraPwhaRJj9pDY8NBhA3ikzy823pW"
    assert launch.user == "DT3tf6Gn38tvpKLWiNNztAYS552AvYqsYi5RxGo8A2XV"
    assert launch.token_program == "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
    # Pump CreateEvent native SOL icin zero-pubkey sentinel kullaniyor.
    assert launch.quote_mint == "11111111111111111111111111111111"
    assert launch.token_total_supply == 1_000_000_000_000_000


def test_decodes_real_buy_trade_fixture_and_ignores_create_event():
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "pump_trade_buy.json").read_text("utf-8")
    )
    trades = decode_pump_trade_logs(fixture["logs"])
    assert len(trades) == 1
    trade = trades[0]
    assert trade.mint == "Dv9QuFg6z6dhR5s6tWW5u8fjn99mVDnYKamyrnKFpump"
    assert trade.is_buy is True
    assert trade.ix_name == "buy"
    assert trade.user == "4YZdqpUf2ZUCaPN6EMNygQjmcqLA8HaXjEhGjoXZ35DD"
    assert trade.token_amount == 2_291_228_580_126
    assert trade.effective_quote_amount == 64_197_529
    assert trade.virtual_quote_reserves == 30_064_197_529
    assert trade.quote_asset == "SOL"
