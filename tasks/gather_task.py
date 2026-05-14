from venv import logger

from models import Character
from services.gathering import GatherService
from tasks import Task


class GatherTask(Task):
    def __init__(self, node, gathering_service: GatherService):
        self.node = node
        self.gathering_service = gathering_service

    async def execute_step(self, character: Character) -> bool:
        if character.position.x != self.node.x or character.position.y != self.node.y:
            logger.warning(
                "%s n'est pas sur le node %s pour récolter %s",
                character.name,
                self.node,
                self.node.resource_code,
            )
            return True

        await self.gathering_service.gather_resources(
            character, self.node.resource_code
        )
        return True
