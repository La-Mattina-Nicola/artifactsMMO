from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from game.character_controller import CharacterController
from services import MovementService, GatherService, CraftingService
from services.banking import BankService
from services.deposit import DepositService
from services.fighting import FightingService
from services.resting import RestingService
from tasks import MoveToTask, GoalTask
from tasks.craft_task import CraftTask
from routines import GatheringRoutine

if TYPE_CHECKING:
    from data.world import World
    from models import Character

logger = logging.getLogger(__name__)


class BaseManager:
    def __init__(
        self,
        characters: list[Character],
        gateway,
        world: World,
        bank_service: BankService,
    ):
        self.gateway = gateway
        self.world = world
        self.bank_service = bank_service
        self.characters = {c.name: c for c in characters}

        self.movement_service = MovementService(gateway)
        self.gathering_service = GatherService(gateway)
        self.crafting_service = CraftingService(gateway, world)
        self.deposit_service = DepositService(gateway, self.movement_service, world)
        self.fighting_service = FightingService(gateway)
        self.rest_service = RestingService(gateway)

        self.controllers = {
            c.name: CharacterController(c, self.deposit_service, self.rest_service)
            for c in characters
        }

    async def cmd_farm(self, name: str, drop_code: str, qty: int | None = None):
        if name not in self.controllers:
            logger.warning("Perso inconnu : %s", name)
            return

        character = self.characters[name]
        node = self.world.closest_node(
            drop_code, character.position.x, character.position.y
        )
        if node is None:
            logger.warning("Ressource inconnue : %s", drop_code)
            return

        routine = GatheringRoutine(
            drop_code=drop_code,
            world=self.world,
            movement_service=self.movement_service,
            gathering_service=self.gathering_service,
        )

        if qty is None:
            self.controllers[name].set_default(routine)
            logger.info("%s — farm %s en boucle", name, drop_code)
        else:
            condition = make_farm_condition(drop_code, qty)
            self.controllers[name].set_todo(GoalTask(routine, condition))
            logger.info("%s — farm %s jusqu'à %d", name, drop_code, qty)

    async def cmd_craft(self, name: str, item_code: str, quantity: int):
        if name not in self.controllers:
            logger.warning("Perso inconnu : %s", name)
            return

        item = self.world.items.get(item_code)
        if item is None:
            logger.warning("Item inconnu : %s", item_code)
            return

        if item.craft is None:
            logger.warning("Item non craftable : %s", item_code)
            return

        task = CraftTask(
            item=item,
            quantity=quantity,
            bank_service=self.bank_service,
            craft_service=self.crafting_service,
            movement_service=self.movement_service,
        )
        self.controllers[name].set_priority(task)
        logger.info("%s — craft %dx %s", name, quantity, item.name)

    async def cmd_move(self, name: str, x: int, y: int):
        if name not in self.controllers:
            logger.warning("Perso inconnu : %s", name)
            return
        task = MoveToTask(x, y, self.movement_service)
        self.controllers[name].set_priority(task)
        logger.info("%s — déplacement vers (%d, %d)", name, x, y)

    async def cmd_stop(self, name: str):
        if name not in self.controllers:
            logger.warning("Perso inconnu : %s", name)
            return
        c = self.controllers[name]
        c.priority_task = []
        c.todo_task = None
        c.default_routine = None
        logger.info("%s — arrêté", name)

    async def load_defaults(self):
        config_file = Path("config/characters.json")
        if not config_file.exists():
            logger.info("Pas de config defaults trouvée")
            return

        config = json.loads(config_file.read_text(encoding="utf-8"))
        for name, settings in config.items():
            if name not in self.controllers:
                logger.warning("Perso inconnu dans config : %s", name)
                continue

            command = settings.get("default")
            args = settings.get("args", [])

            if command == "farm":
                qty = int(args[1]) if len(args) > 1 else None
                await self.cmd_farm(name, args[0], qty)
            elif command == "craft":
                await self.cmd_craft(name, args[0], int(args[1]))
            elif command == "stop":
                await self.cmd_stop(name)

            logger.info("%s — default chargé : %s %s", name, command, args)

    async def _controllers_loop(self):
        await asyncio.gather(*(c.main_loop() for c in self.controllers.values()))


def make_farm_condition(drop_code: str, qty: int):
    def condition(c):
        return c.inventory.count(drop_code) >= qty

    return condition
