from api import ArtifactsGateway
from data.world import World
from models import Character, Item


class CraftingService:
    def __init__(self, gateway: ArtifactsGateway, world: "World"):
        self.gateway = gateway
        self.world = world

    async def craft(self, character: Character, item: Item, quantity: int = 1):
        await self.gateway.craft(character.name, item.code, quantity)

    async def get_workshop(self, item: Item) -> tuple[int, int]:
        skill = item.craft.skill
        coords = self.world.workshops.get(skill)
        if coords is None:
            raise ValueError(f"Atelier inconnu pour le skill : {skill}")
        return coords
