from __future__ import annotations


class SlotTracker:
    def __init__(self, last_slot: int | None = None):
        self.last_slot = last_slot

    def observe(self, slot: int) -> tuple[int, int] | None:
        if self.last_slot is None:
            self.last_slot = slot
            return None
        if slot <= self.last_slot:
            return None
        previous = self.last_slot
        self.last_slot = slot
        if slot > previous + 1:
            return previous + 1, slot - 1
        return None
