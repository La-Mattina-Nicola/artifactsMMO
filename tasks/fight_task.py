import logging
from models import Character
from services.fighting import FightingService
from tasks import Task
from tasks.exceptions import HealthPointTooLowError, InventoryFullError


logger = logging.getLogger(__name__)


class FighterTask(Task):
    def __init__(self, monster_node, fight_service: FightingService):
        self.monster_node = monster_node
        self.fight_service = fight_service

    async def execute_step(self, character: Character) -> bool:
        if character.stats.hp < (character.stats.max_hp // 2):
            raise HealthPointTooLowError()
        if character.inventory.is_full():
            raise InventoryFullError()
        if (
            character.position.x != self.monster_node.x
            or character.position.y != self.monster_node.y
        ):
            logger.warning(
                "%s n'est pas sur le monster %s pour combattre %s",
                character.name,
                self.monster_node,
                self.monster_node.content_code,
            )
            return False

        await self.fight_service.fight(character)
        return True
