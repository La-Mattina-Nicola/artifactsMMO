import asyncio
import logging
from datetime import datetime, timezone

from models import Character
from services.banking import BankService
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
        bank_service: BankService,
        rest_service: RestingService,
    ):
        self.character = character
        self.bank_service = bank_service
        self.rest_service = rest_service
        self.priority_task: list[Task] = []
        self.todo_task: Task | None = None
        self.default_routine = None
        self.on_delegation_needed = None

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
            logger.debug("%s — cooldown %.1fs", self.character.name, remaining)
            await asyncio.sleep(remaining)
        else:
            await asyncio.sleep(0.1)

    async def main_loop(self):

        logger.debug("%s — main_loop démarré", self.character.name)
        active_task: Task | None = None

        while True:
            await self._wait_cooldown()
            # 1. Si une tâche est en cours → continuer
            if active_task is not None:
                source = "ACTIVE"

            # 2. Sinon → choisir une nouvelle tâche
            elif self.priority_task:
                active_task = self.priority_task[-1]
                source = "PRIORITY"

            elif self.todo_task:
                active_task = self.todo_task
                logger.info(
                    "%s — nouvelle tâche TODO : %s",
                    self.character.name,
                    active_task.__class__.__name__,
                )
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
                await asyncio.sleep(0.1)
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
                    # nettoyer la source
                    if source == "PRIORITY":
                        self.priority_task.pop()
                    elif source == "TODO":
                        self.todo_task = None

                    # libérer la tâche active
                    active_task = None

            except InsufficientSkillLevelError as e:
                logger.warning(
                    "%s — niveau %s insuffisant (requis: lv.%d)",
                    self.character.name,
                    e.skill,
                    e.required_level,
                )
                if self.on_delegation_needed:
                    await self.on_delegation_needed(
                        self.character,
                        e.skill,
                        e.required_level,
                        e.item_code,
                        e.quantity,
                    )
                # Vider le slot — qu'il y ait délégation ou non
                if source == "PRIORITY":
                    self.priority_task.pop()
                elif source == "TODO":
                    self.todo_task = None
                elif source == "DEFAULT":
                    self.default_routine = (
                        None  # ← stopper la routine si délégation impossible
                    )
                active_task = None
                await asyncio.sleep(5)
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
                active_task = None
                continue
            except (InventoryFullError, InventoryNotEmptyError):
                logger.debug(f"INJECT DEPOSIT TASK pour {self.character.name}")

                self.priority_task.append(DepositTask(self.bank_service))
                logger.debug(f"priority_task = {self.priority_task}")
                active_task = None

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
                active_task = None
