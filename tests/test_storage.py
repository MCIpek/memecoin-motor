from pathlib import Path
import json

from memecoin_motor.models import ChainEvent, SlotGap, TokenObservation
from memecoin_motor.storage import Storage
from memecoin_motor.pump_decoder import PumpLaunch, decode_pump_trade_logs


def test_storage_is_idempotent(tmp_path: Path):
    storage = Storage(tmp_path / "test.db")
    storage.initialize()
    event = ChainEvent(
        signature="sig", slot=12, program_id="program", commitment="confirmed",
        client_received_at="now", processed_at="now", provider_name="test",
    )
    assert storage.save_event(event) is True
    assert storage.save_event(event) is False
    token = TokenObservation("mint", "creator", "program", 12, None, "sig", "now", "PARTIAL")
    assert storage.save_token(token) is True
    assert storage.save_token(token) is False
    storage.save_gap(SlotGap(10, 11, "now", "test"))
    assert storage.counts() == {
        "chain_events": 1, "tokens_minimal": 1,
        "pump_launches": 0, "pump_trades": 0, "wallet_positions": 0,
        "snapshot_tracking": 0, "token_snapshots": 0, "stream_gaps": 1,
        "wallet_analysis_queue": 0, "wallet_profiles": 0, "wallet_edges": 0,
        "risk_decisions": 0, "paper_positions": 0, "paper_outcomes": 0,
        "market_outcomes": 0, "transaction_enrichment_queue": 0,
        "early_trade_metadata": 0, "sniper_scores": 0,
            "wallet_behavior_stats": 0, "paper_v2_positions": 0,
            "executable_outcomes_v2": 0, "x_band_calibration": 0
        }
    storage.close()


def test_wallet_queue_is_bounded_and_saves_graph_edge(tmp_path: Path):
    storage = Storage(tmp_path / "wallet.db")
    storage.initialize()
    assert storage.enqueue_early_buyer("a", "mint", 1, "now")
    assert not storage.enqueue_early_buyer("b", "mint", 1, "now")
    item = storage.claim_wallet_analysis(1)
    assert item is not None and item["address"] == "a"
    storage.save_wallet_analysis(
        item["id"], "a", 7, False, "old", 10, "funder", "funding-sig",
        1_000_000, 9, "RECENT_FUNDING_CANDIDATE", 0.55,
    )
    profile = storage.wallet_profile("a")
    assert profile is not None
    assert profile["likely_funder"] == "funder"
    assert profile["history_complete"] == 0
    assert storage.counts()["wallet_edges"] == 1
    storage.close()


def test_trade_updates_wallet_and_event_time_snapshot(tmp_path: Path):
    storage = Storage(tmp_path / "trade.db")
    storage.initialize()
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "pump_trade_buy.json").read_text("utf-8")
    )
    trade = decode_pump_trade_logs(fixture["logs"])[0]
    launch_event = ChainEvent(
        signature="launch-sig", slot=fixture["slot"], program_id="program",
        commitment="confirmed", client_received_at="now", processed_at="now",
        provider_name="test",
    )
    storage.save_event(launch_event)
    launch = PumpLaunch(
        instruction_name="create_v2", name="Wife", symbol="WIFE", uri="uri",
        mint=trade.mint, bonding_curve="curve", user=trade.user,
        creator=trade.creator, timestamp=trade.timestamp,
        virtual_token_reserves=1_073_000_000_000_000,
        virtual_sol_reserves=30_000_000_000,
        real_token_reserves=793_100_000_000_000,
        token_total_supply=1_000_000_000_000_000,
        token_program="token", is_mayhem_mode=True,
        is_cashback_enabled=False, quote_mint="11111111111111111111111111111111",
        virtual_quote_reserves=30_000_000_000,
    )
    storage.save_pump_launch(
        launch, "launch-sig", fixture["slot"], trade.timestamp, "now"
    )
    storage.enable_snapshot_tracking(trade.mint, trade.timestamp, "now")
    trade_event = ChainEvent(
        signature=fixture["signature"], slot=fixture["slot"], program_id="program",
        commitment="confirmed", client_received_at="now", processed_at="now",
        provider_name="test",
    )
    storage.save_event(trade_event)
    assert storage.save_trade(trade, fixture["signature"], fixture["slot"], "now")
    assert not storage.save_trade(trade, fixture["signature"], fixture["slot"], "now")
    position = storage.wallet_position(trade.mint, trade.user)
    assert position is not None
    assert position["buy_count"] == 1
    assert position["buy_token_amount"] == trade.token_amount
    assert storage.create_due_snapshots(trade.timestamp + 2) == 1
    snapshot = storage.snapshot(trade.mint, 2)
    assert snapshot is not None
    assert snapshot["trade_count"] == 1
    assert snapshot["unique_buyers"] == 1
    assert snapshot["net_quote_flow"] == trade.effective_quote_amount
    assert snapshot["top_buyer_share"] == 1.0
    storage.close()
