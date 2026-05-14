from dataclasses import dataclass, field
from typing import List
from models.inventory_item import InventoryItem


@dataclass
class Inventory:
    max_items: int
    items: List[InventoryItem] = field(default_factory=list)

    def count(self, code: str) -> int:
        return sum(i.quantity for i in self.items if i.code == code)

    def has(self, code: str) -> bool:
        return self.count(code) > 0

    def add(self, code: str, qty: int):
        for item in self.items:
            if item.code == code:
                item.quantity += qty
                return
        self.items.append(InventoryItem(slot=-1, code=code, quantity=qty))

    def remove(self, code: str, qty: int):
        for item in self.items:
            if item.code == code:
                item.quantity -= qty
                if item.quantity <= 0:
                    self.items.remove(item)
                return

    def is_full(self) -> bool:
        cpt = 0
        for item in self.items:
            cpt += item.quantity
        return cpt >= self.max_items
