import asyncio
import logging
from datetime import datetime, timezone

from models import Character
from services.deposit import DepositService
from tasks.base_task import Task


from tasks.exceptions import InventoryFullError
from tasks.deposit_task import DepositTask

logger = logging.getLogger(__name__)


class CharacterController:
    def __init__(self, character: Character, deposit_service: DepositService):
        self.character = character
        self.deposit_service = deposit_service
        self.priority_task: Task | None = None
        self.todo_task: Task | None = None
        self.default_routine = None

    def set_priority(self, task: Task):
        self.priority_task = task

    def set_todo(self, task: Task):
        self.todo_task = task

    def set_default(self, routine):
        self.default_routine = routine

    async def _wait_cooldown(self):
        expiration = self.character.cooldowns.expiration
        now = datetime.now(timezone.utc)
        remaining = (expiration - now).total_seconds()
        if remaining > 0:
            await asyncio.sleep(remaining)

    async def main_loop(self):
        while True:
            await self._wait_cooldown()

            if self.priority_task:
                active_task = self.priority_task
                source = "PRIORITY"

            elif self.todo_task:
                active_task = self.todo_task
                source = "TODO"

            elif self.default_routine:
                active_task = self.default_routine.generate_task(self.character)
                source = "DEFAULT"
                logger.debug(
                    "%s — tâche générée : %s",
                    self.character.name,
                    active_task.__class__.__name__,
                )

            else:
                await asyncio.sleep(0.5)
                continue
            logger.debug(
                "%s — exécute %s [%s]",
                self.character.name,
                active_task.__class__.__name__,
                source,
            )

            try:
                done = await active_task.execute_step(self.character)

                if done:
                    if source == "PRIORITY":
                        self.priority_task = None
                    elif source == "TODO":
                        self.todo_task = None

            except InventoryFullError:
                logger.debug(f"INJECT DEPOSIT TASK pour {self.character.name}")
                self.priority_task = DepositTask(self.deposit_service)
                logger.debug(f"priority_task = {self.priority_task}")

            except Exception as e:
                logger.error("%s — erreur : %s", self.character.name, str(e))
                await asyncio.sleep(1)
                if not active_task.retry_on_fail:
                    if source == "PRIORITY":
                        self.priority_task = None
                    elif source == "TODO":
                        self.todo_task = None
