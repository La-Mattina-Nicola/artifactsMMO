# tasks/trade_task.py
import logging
from tasks.base_task import Task

logger = logging.getLogger(__name__)


class TradeTask(Task):
    retry_on_fail = False

    def __init__(self, tasking_service, item_code: str, quantity: int):
        self.tasking_service = tasking_service
        self.item_code = item_code
        self.quantity = quantity

    async def execute_step(self, character) -> bool:
        logger.debug("TRADE: échange de %dx %s", self.quantity, self.item_code)
        await self.tasking_service.trade_task(character, self.item_code, self.quantity)
        logger.info("%s — trade %dx %s", character.name, self.quantity, self.item_code)
        return True
