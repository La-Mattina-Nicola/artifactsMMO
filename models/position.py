from dataclasses import dataclass


@dataclass
class Position:
    x: int
    y: int
    layer: str
    map_id: int
