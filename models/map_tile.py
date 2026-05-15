from dataclasses import dataclass


@dataclass
class MapTile:
    map_id: int
    name: str
    x: int
    y: int
    layer: str
    content_type: str | None
    content_code: str | None
