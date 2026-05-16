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
            logger.info(
                "%s est déjà à plein de vie, pas besoin de se reposer", character.name
            )
            return True
        logger.info("%s se repose pour récupérer de la vie", character.name)
        await self.rest_service.rest(character)
        return True
