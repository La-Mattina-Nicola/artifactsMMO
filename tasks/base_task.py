from abc import ABC, abstractmethod
from models import Character


class Task(ABC):
    retry_on_fail: bool = True

    @abstractmethod
    async def execute_step(self, character: Character) -> bool:
        """Retourne True quand la tâche est terminée."""
        pass
