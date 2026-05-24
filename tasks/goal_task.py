from models import Character
from tasks import Task


class GoalTask(Task):
    def __init__(self, item_code: str, target_quantity: int, routine):
        self.item_code = item_code
        self.target_quantity = target_quantity
        self.routine = routine
        self.current_task = None
        self._initial_count = None
        self._last_count = 0
        self._banked = 0  # ← total déposé en banque

    async def execute_step(self, character: Character) -> bool:
        if self._initial_count is None:
            self._initial_count = character.inventory.count(self.item_code)
            self._last_count = self._initial_count

        current = character.inventory.count(self.item_code)

        if current < self._last_count:
            self._banked += self._last_count - current
        self._last_count = current

        total_collected = (current - self._initial_count) + self._banked
        if total_collected >= self.target_quantity:
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
