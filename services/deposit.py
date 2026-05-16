from models.character import Character
from services.movement import MovementService
from data.world import World


class DepositService:
    def __init__(self, gateway, movement_service: MovementService, world: World):
        self.gateway = gateway
        self.movement_service = movement_service
        self.world = world

    def _closest_bank(self, x: int, y: int) -> tuple[int, int]:
        return min(self.world.banks, key=lambda b: abs(b[0] - x) + abs(b[1] - y))

    async def deposit_all(self, character: Character):
        bx, by = self._closest_bank(character.position.x, character.position.y)

        if character.position.x != bx or character.position.y != by:
            await self.movement_service.move(character, bx, by)

        items = [
            {"code": item.code, "quantity": item.quantity}
            for item in character.inventory.items
        ]
        if items:
            dto = await self.gateway.deposit_items(character.name, items)
            character.update_from_dto({"data": dto["data"]["character"]})
