import logging
from models.item import Item
from data.world import World
from api import ArtifactsGateway

logger = logging.getLogger(__name__)


class BankService:
    def __init__(self, gateway: "ArtifactsGateway", world: "World"):
        self.gateway = gateway
        self.world = world
        self.items: dict[str, int] = {}
    
    async def load(self):
        items = await self.gateway.get_bank_items()
        self.items = {item["code"]: item["quantity"] for item in items}
        logger.info("Banque chargée — %d items", len(self.items))

    def closest_bank(self, x: int, y: int) -> tuple[int, int]:
        return min(self.world.banks, key=lambda b: abs(b[0] - x) + abs(b[1] - y))

    async def has_ingredients(self, item: Item, quantity: int) -> bool:
        for ingredient in item.craft.items:
            available = self.items.get(ingredient.code, 0)
            if available < ingredient.quantity * quantity:
                return False
        return True

    async def withdraw_ingredients(self, character, item: Item, quantity: int):
        items = [
            {"code": ing.code, "quantity": ing.quantity * quantity}
            for ing in item.craft.items
        ]
        dto = await self.gateway.withdraw_items(character, items)
        character.update_from_dto({"data": dto["data"]["character"]})
        for ing in item.craft.items:
            self.items[ing.code] = self.items.get(ing.code, 0) - ing.quantity * quantity
