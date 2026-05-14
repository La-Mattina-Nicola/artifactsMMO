from dataclasses import dataclass


@dataclass
class SkillLevel:
    level: int
    xp: int
    max_xp: int
