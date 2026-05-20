import logging

from services.banking import BankService
from tasks.base_task import Task
from models import Character

logger = logging.getLogger(__name__)


class DepositTask(Task):
    def __init__(self, bank_service: BankService):
        self.bank_service = bank_service
        self._step = 0
        self._move_task = None  # ← stocker le MoveToTask

    async def execute_step(self, character: Character) -> bool:
        if self._step == 0:
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
            self._step = 1
            return False

        if self._step == 1:
            items = [
                {"code": item.code, "quantity": item.quantity}
                for item in character.inventory.items
            ]
            if items:
                await self.bank_service.gateway.deposit_items(character, items)
                for item in items:
                    self.bank_service.items[item["code"]] = (
                        self.bank_service.items.get(item["code"], 0) + item["quantity"]
                    )
            return True
