import logging
from models import Character
from tasks import Task
from services import RestingService

logger = logging.getLogger(__name__)


class RestTask(Task):
    def __init__(self, rest_service: RestingService):
        self.rest_service = rest_service

    async def execute_step(self, character: Character) -> bool:
        if character.stats.hp >= character.stats.max_hp:
            return True

        food = self.rest_service.best_food_in_inventory(character)
        if food:
            missing = character.stats.max_hp - character.stats.hp
            heal = food.heal_value()
            if heal > 0:
                available = character.inventory.count(food.code)
                qty = min(missing // heal, available)
                if qty > 0:
                    await self.rest_service.gateway.use_item(
                        character, food.code, quantity=qty
                    )
                    return False

        if character.stats.hp >= (character.stats.max_hp // 2 + 50):
            return True
        logger.info("%s se repose pour récupérer de la vie", character.name)
        await self.rest_service.rest(character)
        return True
