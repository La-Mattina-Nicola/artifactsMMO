from models import Character
from tasks.base_task import Task
from services.movement import MovementService


class MoveToTask(Task):
    def __init__(self, x: int, y: int, movement_service: MovementService):
        self.x = x
        self.y = y
        self.movement_service = movement_service

    async def execute_step(self, character: Character) -> bool:
        if character.position.x == self.x and character.position.y == self.y:
            return True

        await self.movement_service.move(character, self.x, self.y)
        return True
