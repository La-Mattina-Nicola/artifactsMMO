from dataclasses import dataclass


@dataclass
class CharacterTask:
    name: str
    type: str
    progress: int
    total: int

    def __str__(self):
        name = self.name
        if len(name) > 18:
            name = name[:15] + "..."
        else:
            name = name.ljust(18)
        return name
