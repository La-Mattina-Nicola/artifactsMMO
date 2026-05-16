from api import ArtifactsGateway
from models import Character


class FightingService:
    def __init__(self, gateway: ArtifactsGateway):
        self.gateway = gateway

    async def fight(self, character: Character):
        await self.gateway.fight(character)
