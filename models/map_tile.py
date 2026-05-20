from dataclasses import dataclass, field


@dataclass
class MapTile:
    map_id: int
    name: str
    x: int
    y: int
    layer: str
    content_type: str | None
    content_code: str | None
    transition_x: int | None = None
    transition_y: int | None = None
    transition_layer: str | None = None
    transition_conditions: list = field(default_factory=list)
