from dataclasses import dataclass


@dataclass
class Equipment:
    weapon: str
    rune: str
    shield: str
    helmet: str
    body_armor: str
    leg_armor: str
    boots: str
    ring1: str
    ring2: str
    amulet: str
    artifact1: str
    artifact2: str
    artifact3: str
    utility1: tuple[str, int]
    utility2: tuple[str, int]
    bag: str
