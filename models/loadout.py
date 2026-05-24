from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LoadoutPlan:
    equip_changes: dict[str, str]
    withdraw_items: dict[str, int]
    food_code: str | None = None
    food_needed: int = 0

    def has_actions(self) -> bool:
        return bool(self.equip_changes or self.withdraw_items)
