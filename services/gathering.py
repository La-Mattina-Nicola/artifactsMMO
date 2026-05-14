from api import ArtifactsGateway
from models import Character


class GatherService:
    def __init__(self, gateway: ArtifactsGateway):
        self.gateway = gateway

    async def gather_resources(self, character: Character, resource: str):
        await self.gateway.gather(character)
