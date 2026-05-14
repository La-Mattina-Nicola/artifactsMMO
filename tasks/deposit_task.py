from asyncio.log import logger

from tasks.base_task import Task
from models import Character
from services.deposit import DepositService


class DepositTask(Task):
    retry_on_fail = True

    def __init__(self, deposit_service: DepositService):
        self.deposit_service = deposit_service
        self._moved = False

    async def execute_step(self, character: Character) -> bool:
        try:
            bx, by = self.deposit_service._closest_bank(
                character.position.x, character.position.y
            )
            logger.debug(
                f"DEPOSIT: pos={character.position.x},{character.position.y} bank={bx},{by}"
            )

            if character.position.x != bx or character.position.y != by:
                logger.debug(f"DEPOSIT: déplacement vers banque {bx},{by}")
                await self.deposit_service.movement_service.move(character, bx, by)
                logger.debug(f"DEPOSIT: déplacement terminé")
                return False

            logger.debug(f"DEPOSIT: dépôt des items")

            items = [
                {"code": item.code, "quantity": item.quantity}
                for item in character.inventory.items
            ]
            if items:
                await self.deposit_service.gateway.deposit_items(character, items)

            return True
        except Exception as e:
            logger.debug(f"DEPOSIT ERROR: {e}")
            raise
