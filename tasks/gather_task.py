import logging
from models import Character
from services.gathering import GatherService
from tasks import Task
from tasks.exceptions import InventoryFullError


logger = logging.getLogger(__name__)


class GatherTask(Task):
    def __init__(self, node, gathering_service: GatherService):
        self.node = node
        self.gathering_service = gathering_service

    async def execute_step(self, character: Character) -> bool:
        if character.inventory.is_full():
            raise InventoryFullError()
        if character.position.x != self.node.x or character.position.y != self.node.y:
            logger.warning(
                "%s n'est pas sur le node %s pour récolter %s",
                character.name,
                self.node,
                self.node.content_code,
            )
            return False

        await self.gathering_service.gather_resources(character)
        return True
