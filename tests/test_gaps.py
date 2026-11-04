from memecoin_motor.gaps import SlotTracker


def test_contiguous_slots_do_not_create_gap():
    tracker = SlotTracker(10)
    assert tracker.observe(11) is None
    assert tracker.observe(12) is None


def test_missing_slots_create_exact_gap():
    tracker = SlotTracker(10)
    assert tracker.observe(14) == (11, 13)
    assert tracker.last_slot == 14


def test_old_or_duplicate_slot_is_ignored():
    tracker = SlotTracker(10)
    assert tracker.observe(10) is None
    assert tracker.observe(9) is None
    assert tracker.last_slot == 10

