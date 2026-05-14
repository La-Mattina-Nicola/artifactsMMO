from dataclasses import dataclass


@dataclass
class CharacterTask:
    name: str
    type: str
    progress: int
    total: int
