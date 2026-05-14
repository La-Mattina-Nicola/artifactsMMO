from dataclasses import dataclass


@dataclass
class InventoryItem:
    slot: int
    code: str
    quantity: int
