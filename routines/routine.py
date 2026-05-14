from abc import ABC, abstractmethod
from tasks import Task


class Routine(ABC):
    @abstractmethod
    def generate_task(self, character) -> Task:
        pass
