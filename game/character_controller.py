import asyncio
import logging
from datetime import datetime, timezone

from models import Character
from services.deposit import DepositService
from services.resting import RestingService
from tasks.base_task import Task


from tasks.exceptions import (
    HealthPointTooLowError,
    InsufficientSkillLevelError,
    InventoryFullError,
    InventoryNotEmptyError,
)
from tasks.deposit_task import DepositTask
from tasks.rest_task import RestTask

logger = logging.getLogger(__name__)


class CharacterController:
    def __init__(
        self,
        character: Character,
        deposit_service: DepositService,
        rest_service: RestingService,
    ):
        self.character = character
        self.deposit_service = deposit_service
        self.rest_service = rest_service
        self.priority_task: list[Task] = []
        self.todo_task: Task | None = None
        self.default_routine = None

    def set_priority(self, task: Task):
        self.priority_task.append(task)

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

            if self.priority_task and len(self.priority_task) > 0:
                active_task = self.priority_task[-1]
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
                        self.priority_task.pop()
                    elif source == "TODO":
                        self.todo_task = None

            except InsufficientSkillLevelError as e:
                logger.warning(
                    "%s - délégation nécessaire pour %s",
                    self.character.name,
                    e.item.name,
                )
                if self.on_delegation_needed:
                    await self.on_delegation_needed(self.character, e.item, e.quantity)
                if source == "PRIORITY":
                    self.priority_task.pop()
                elif source == "TODO":
                    self.todo_task = None
            except HealthPointTooLowError:
                logger.warning(
                    "%s n'a pas assez de points de vie pour exécuter %s",
                    self.character.name,
                    active_task.__class__.__name__,
                )
                self.priority_task.append(RestTask(self.rest_service))
            except (InventoryFullError, InventoryNotEmptyError):
                logger.debug(f"INJECT DEPOSIT TASK pour {self.character.name}")

                self.priority_task.append(DepositTask(self.deposit_service))
                logger.debug(f"priority_task = {self.priority_task}")

            except StopIteration as e:
                logger.info("%s — routine terminée : %s", self.character.name, str(e))
                if source == "DEFAULT":
                    self.default_routine = None

            except Exception as e:
                import traceback

                logger.error(
                    "%s — erreur : %s\n%s",
                    self.character.name,
                    str(e),
                    traceback.format_exc(),
                )
                await asyncio.sleep(1)
                if not active_task.retry_on_fail:
                    if source == "PRIORITY":
                        self.priority_task.pop()
                    elif source == "TODO":
                        self.todo_task = None
