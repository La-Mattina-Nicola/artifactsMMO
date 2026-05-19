import logging

from services.banking import BankService
from tasks.base_task import Task
from models import Character

logger = logging.getLogger(__name__)


class DepositTask(Task):
    retry_on_fail = True

    def __init__(self, bank_service: BankService):
        self.bank_service = bank_service
        self._step = 0

    async def execute_step(self, character: Character) -> bool:
        # Step 0 — se déplacer à la banque
        if self._step == 0:
            bx, by = self.bank_service.closest_bank(
                character.position.x, character.position.y
            )
            if character.position.x != bx or character.position.y != by:
                await self.bank_service.movement_service.move(character, bx, by)
                return False
            self._step = 1
            return False

        # Step 1 — déposer
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
