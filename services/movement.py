from api import ArtifactsGateway
from data.world import World
from models import Character


class MovementService:
    def __init__(self, gateway: ArtifactsGateway, world: World):
        self.gateway = gateway
        self.world = world

    async def move(self, character: Character, x: int, y: int):
        await self.gateway.move(character, x, y)

    def find_transition(self, x: int, y: int, current_layer: str, target_layer: str):
        """Trouve la transition sans conditions la plus proche vers target_layer."""
        candidates = [
            tile
            for tile in self.world.maps.values()
            if tile.layer == current_layer
            and tile.transition_layer == target_layer
            and not tile.transition_conditions
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda t: abs(t.x - x) + abs(t.y - y))
