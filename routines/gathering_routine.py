from routines import Routine
from tasks.gather_task import GatherTask
from tasks.move_task import MoveToTask


class GatheringRoutine(Routine):
    def __init__(self, node, movement_service, gathering_service):
        self.node = node
        self.movement_service = movement_service
        self.gathering_service = gathering_service

    def generate_task(self, character):
        if character.position.map_id != self.node.map_id:
            return MoveToTask(self.node.x, self.node.y, self.movement_service)

        return GatherTask(self.node, self.gathering_service)
