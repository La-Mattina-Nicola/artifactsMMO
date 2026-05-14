from api import ArtifactsGateway
from models import Character


class CraftingService:
    def __init__(self, gateway: ArtifactsGateway):
        self.gateway = gateway

    async def craft_item(self, character: Character, item: str):
        dto = await self.gateway.craft(character.name, item)
        character.update_from_dto({"data": dto["data"]["character"]})
