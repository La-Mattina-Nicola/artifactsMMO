from api import ArtifactsGateway
from models import Character


class GatherService:
    def __init__(self, gateway: ArtifactsGateway):
        self.gateway = gateway

    async def gather_resources(self, character: Character, resource: str):
        dto = await self.gateway.gather(character.name, resource)
        character.update_from_dto({"data": dto["data"]["character"]})
