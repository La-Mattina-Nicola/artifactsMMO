from typing import Callable
from models import Character
from tasks import Task


class GoalTask(Task):
    def __init__(self, routine, condition: Callable[[Character], bool]):
        self.routine = routine
        self.condition = condition

    async def execute_step(self, character: Character) -> bool:
        if self.condition(character):
            return True

        sub_task = self.routine.generate_task(character)
        return await sub_task.execute_step(character)
