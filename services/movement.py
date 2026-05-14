from api import ArtifactsGateway
from models import Character


class MovementService:
    def __init__(self, gateway: ArtifactsGateway):
        self.gateway = gateway

    async def move_character(self, character: Character, x: int, y: int):
        dto = await self.gateway.move(character.name, x, y)
        character.update_from_dto({"data": dto["data"]["character"]})
