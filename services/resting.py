from api import ArtifactsGateway
from data.world import World
from models import Character, Item
from services.banking import BankService


class RestingService:
    def __init__(
        self, gateway: ArtifactsGateway, world: World, bank_service: BankService
    ):
        self.gateway = gateway
        self.world = world
        self.bank_service = bank_service

    async def rest(self, character: Character):
        await self.gateway.rest(character)

    def best_food_in_inventory(self, character) -> Item | None:
        foods = [
            self.world.items[i.code]
            for i in character.inventory.items
            if (item := self.world.items.get(i.code)) and item.is_food()
        ]
        if not foods:
            return None
        return max(foods, key=lambda item: item.heal_value())

    def best_food_in_bank(self, character) -> Item | None:
        foods = [
            self.world.items[code]
            for code, qty in self.bank_service.items.items()
            if qty > 0
            and (item := self.world.items.get(code))
            and item.is_food()
            and item.can_equip(character)
        ]
        if not foods:
            return None
        return max(foods, key=lambda item: item.heal_value())
