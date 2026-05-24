import logging
from tasks.base_task import Task

logger = logging.getLogger(__name__)


class AcceptTask(Task):
    retry_on_fail = False

    def __init__(self, tasking_service):
        self.tasking_service = tasking_service

    async def execute_step(self, character) -> bool:
        await self.tasking_service.accept_task(character)
        logger.info(
            "%s — nouvelle quête acceptée : %s", character.name, character.task.name
        )
        return True
