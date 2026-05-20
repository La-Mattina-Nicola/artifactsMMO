import logging
from models.item import Item
from services.banking import BankService
from tasks.base_task import Task
from models import Character

logger = logging.getLogger(__name__)


class WithdrawTask(Task):
    retry_on_fail = True

    def __init__(self, bank_service: BankService, item_code: str, quantity: int):
        self.bank_service = bank_service
        self.item_code = item_code
        self.quantity = quantity
        self._move_task = None

    async def execute_step(self, character: Character) -> bool:
        bx, by = self.bank_service.closest_bank(
            character.position.x, character.position.y
        )
        if (
            character.position.x != bx
            or character.position.y != by
            or character.position.layer != "overworld"
        ):
            if self._move_task is None:
                from tasks.move_task import MoveToTask

                self._move_task = MoveToTask(
                    bx, by, self.bank_service.movement_service, layer="overworld"
                )
            done = await self._move_task.execute_step(character)
            if not done:
                return False

        await self.bank_service.withdraw(character, self.item_code, self.quantity)
        return True


class WithdrawIngredientsTask(Task):
    retry_on_fail = True

    def __init__(self, bank_service: BankService, item, quantity: int):
        self.bank_service = bank_service
        self.item = item
        self.quantity = quantity

    async def execute_step(self, character: Character) -> bool:
        bx, by = self.bank_service.closest_bank(
            character.position.x, character.position.y
        )

        if character.position.x != bx or character.position.y != by:
            logger.debug("WITHDRAW ING: déplacement vers banque %d,%d", bx, by)
            await self.bank_service.movement_service.move(character, bx, by)
            return False

        logger.debug(
            "WITHDRAW ING: retrait des ingrédients pour %dx %s",
            self.quantity,
            self.item.code,
        )

        await self.bank_service.withdraw_ingredients(
            character, self.item, self.quantity
        )

        return True
