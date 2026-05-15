from dataclasses import dataclass, field


@dataclass
class ItemEffect:
    code: str
    value: int


@dataclass
class CraftIngredient:
    code: str
    quantity: int


@dataclass
class ItemCraft:
    skill: str
    level: int
    items: list[CraftIngredient]
    quantity: int


@dataclass
class Item:
    name: str
    code: str
    level: int
    type: str
    subtype: str
    effects: list[ItemEffect] = field(default_factory=list)
    craft: ItemCraft | None = None
    tradeable: bool = False
