from venv import logger

from models import Character
from services.gathering import GatherService
from tasks import Task
from tasks.exceptions import InventoryFullError


class GatherTask(Task):
    def __init__(self, node, gathering_service: GatherService, deposit_service=None):
        self.node = node
        self.gathering_service = gathering_service
        self.deposit_service = deposit_service

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
            return True

        await self.gathering_service.gather_resources(
            character,
            self.node.content_code,
        )
        return True

    def _inventory_full(self, character) -> bool:
        total = sum(i.quantity for i in character.inventory.items)
        return total >= character.inventory.max_items
