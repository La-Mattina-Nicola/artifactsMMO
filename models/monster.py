from dataclasses import dataclass, field


@dataclass
class MonsterDrop:
    code: str
    rate: int
    min_quantity: int
    max_quantity: int


@dataclass
class Monster:
    name: str
    code: str
    level: int
    hp: int
    drops: list[MonsterDrop] = field(default_factory=list)
