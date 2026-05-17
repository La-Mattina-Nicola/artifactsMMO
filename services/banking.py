import logging
from models.character import Character
from models.item import Item
from data.world import World
from api import ArtifactsGateway
from services.movement import MovementService

logger = logging.getLogger(__name__)


class BankService:
    def __init__(
        self,
        gateway: ArtifactsGateway,
        world: World,
        movement_service: MovementService = None,
    ):
        self.gateway = gateway
        self.world = world
        self.movement_service = movement_service  # ← ajout
        self.items: dict[str, int] = {}

    def closest_bank(self, x, y) -> tuple[int, int]:
        return min(self.world.banks, key=lambda b: abs(b[0] - x) + abs(b[1] - y))

    async def _move_to_bank(self, character: "Character"):
        bx, by = self.closest_bank(character.position.x, character.position.y)
        if character.position.x != bx or character.position.y != by:
            await self.movement_service.move(character, bx, by)

    async def load(self):
        items = await self.gateway.get_bank_items()
        self.items = {item["code"]: item["quantity"] for item in items}
        logger.info("Banque chargée — %d items", len(self.items))

    async def sync(self):
        await self.load()

    async def deposit_all(self, character: "Character"):
        items = [
            {"code": item.code, "quantity": item.quantity}
            for item in character.inventory.items
        ]
        if items:
            await self.gateway.deposit_items(character, items)
            for item in items:
                self.items[item["code"]] = (
                    self.items.get(item["code"], 0) + item["quantity"]
                )

    async def withdraw(self, character: "Character", item_code: str, quantity: int):
        await self._move_to_bank(character)
        await self.gateway.withdraw_items(
            character, [{"code": item_code, "quantity": quantity}]
        )
        self.items[item_code] = max(0, self.items.get(item_code, 0) - quantity)

    async def withdraw_ingredients(
        self, character: "Character", item: "Item", quantity: int
    ):
        await self._move_to_bank(character)
        items = [
            {"code": ing.code, "quantity": ing.quantity * quantity}
            for ing in item.craft.items
        ]
        await self.gateway.withdraw_items(character, items)
        for ing in item.craft.items:
            self.items[ing.code] = max(
                0, self.items.get(ing.code, 0) - ing.quantity * quantity
            )

    async def has_ingredients(self, item: "Item", quantity: int) -> bool:
        for ing in item.craft.items:
            if self.items.get(ing.code, 0) < ing.quantity * quantity:
                return False
        return True
