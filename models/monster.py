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
    type: str
    hp: int
    attack_fire: int = 0
    attack_earth: int = 0
    attack_water: int = 0
    attack_air: int = 0
    res_fire: int = 0
    res_earth: int = 0
    res_water: int = 0
    res_air: int = 0
    critical_strike: int = 0
    initiative: int = 0
    effects: list[dict] = field(default_factory=list)
    drops: list[MonsterDrop] = field(default_factory=list)
