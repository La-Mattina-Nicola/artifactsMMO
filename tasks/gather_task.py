from models import Character
from tasks import Task


class GatherTask(Task):
    def __init__(self, node, gathering_service):
        self.node = node
        self.gathering_service = gathering_service

    async def execute_step(self, character: Character) -> bool:
        if character.position.map_id != self.node.map_id:
            return False  # la routine générera un MoveToTask

        await self.gathering_service.gather(character)
        return True
