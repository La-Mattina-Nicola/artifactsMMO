from dataclasses import dataclass, field


@dataclass
class ResourceDrop:
    code: str
    rate: int
    min_quantity: int
    max_quantity: int


@dataclass
class Resource:
    name: str
    code: str
    skill: str
    level: int
    drops: list[ResourceDrop] = field(default_factory=list)
