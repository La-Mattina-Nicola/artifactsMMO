from models.character import Character
from tasks.base_task import Task


class MonsterGoalTask(Task):
    def __init__(self, target_progress: int, routine):
        self.target_progress = target_progress
        self.routine = routine
        self.current_task = None

    async def execute_step(self, character: "Character") -> bool:
        if character.task.progress >= self.target_progress:
            return True

        if self.current_task is None:
            self.current_task = self.routine.generate_task(character)

        try:
            done = await self.current_task.execute_step(character)
        except Exception:
            self.current_task = None
            raise

        if done:
            self.current_task = None

        return False
