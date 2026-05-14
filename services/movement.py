from api import ArtifactsGateway
from models import Character


class MovementService:
    def __init__(self, gateway: ArtifactsGateway):
        self.gateway = gateway

    async def move(self, character: Character, x: int, y: int):
        await self.gateway.move(character, x, y)
