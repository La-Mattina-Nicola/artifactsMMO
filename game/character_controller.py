import asyncio
import logging
from datetime import datetime, timezone

from models import Character
from tasks.base_task import Task


logger = logging.getLogger(__name__)


class CharacterController:
    def __init__(self, character: Character):
        self.character = character
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
            # logger.debug("%s attend cooldown %.1fs", self.character.name, remaining)
            await asyncio.sleep(remaining)

    async def main_loop(self):
        while True:
            await asyncio.sleep(3)
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

            except Exception as e:
                logger.error("%s — erreur : %s", self.character.name, e)
                if not active_task.retry_on_fail:
                    if source == "PRIORITY":
                        self.priority_task = None
                    elif source == "TODO":
                        self.todo_task = None
