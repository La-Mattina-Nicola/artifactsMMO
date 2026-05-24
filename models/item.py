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
    conditions: list[dict] = field(default_factory=list)
    effects: list[ItemEffect] = field(default_factory=list)
    craft: ItemCraft | None = None
    tradeable: bool = False

    def is_food(self) -> bool:
        return self.type == "consumable" and self.subtype == "food"

    def heal_value(self) -> int:
        return sum(e.value for e in self.effects if e.code == "heal")

    def can_equip(self, character) -> bool:
        for cond in self.conditions or []:
            if cond.get("code") == "level" and character.level < cond.get("value", 0):
                return False
        return True

    def is_tool_for(self, skill: str) -> bool:
        return (
            self.type == "weapon"
            and self.subtype == "tool"
            and any(e.code == skill for e in self.effects)
        )

    def tool_bonus(self, skill: str) -> int:
        return sum(abs(e.value) for e in self.effects if e.code == skill)
