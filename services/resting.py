from api import ArtifactsGateway
from models import Character


class RestingService:
    def __init__(self, gateway: ArtifactsGateway):
        self.gateway = gateway

    async def rest(self, character: Character):
        await self.gateway.rest(character)
