from asyncio.log import logger

from routines import Routine
from tasks.gather_task import GatherTask
from tasks.move_task import MoveToTask


class GatheringRoutine(Routine):
    def __init__(self, node, movement_service, gathering_service):
        self.node = node
        self.movement_service = movement_service
        self.gathering_service = gathering_service

    def generate_task(self, character):
        # if character.inventory.is_full():
        #     logger.warning(
        #         "%s a l'inventaire plein, ne peut pas récolter", character.name
        #     )
        #     return DepositToBank(self.movement_service, self.trade_service)
        if character.position.x != self.node.x or character.position.y != self.node.y:
            logger.debug(
                "%s n'est pas encore sur le node, génère MoveToTask", character.name
            )
            return MoveToTask(self.node.x, self.node.y, self.movement_service)

        return GatherTask(self.node, self.gathering_service)
