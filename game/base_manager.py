from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from api.artifacts_gateway import ArtifactsGateway
from game.character_controller import CharacterController
from routines.fighting_routine import FightingRoutine
from routines.tasking_routine import TaskingRoutine
from services import MovementService, GatherService, CraftingService
from services import EquipmentService, LoadoutPlanner
from services.banking import BankService
from services.fighting import FightingService
from services.resting import RestingService
from services.tasking import TaskService
from tasks import MoveToTask, GoalTask
from tasks.craft_task import CraftTask
from routines import GatheringRoutine, CraftingRoutine

if TYPE_CHECKING:
    from data.world import World
    from models import Character

logger = logging.getLogger(__name__)


class BaseManager:
    def __init__(
        self,
        characters: list[Character],
        gateway: ArtifactsGateway,
        world: World,
        bank_service: BankService,
    ):
        self.gateway = gateway
        self.world = world
        self.characters = {c.name: c for c in characters}

        self.movement_service = MovementService(gateway, self.world)
        self.gathering_service = GatherService(gateway)
        self.crafting_service = CraftingService(gateway, self.world)
        self.fighting_service = FightingService(gateway)
        self.rest_service = RestingService(gateway, self.world, bank_service)
        self.equipment_service = EquipmentService(gateway)
        self.tasking_service = TaskService(gateway, self.movement_service)

        bank_service.movement_service = self.movement_service
        self.bank_service = bank_service
        self.loadout_planner = LoadoutPlanner(self.world, self.bank_service)

        self.controllers = {}
        for c in characters:
            ctrl = CharacterController(c, self.bank_service, self.rest_service)
            ctrl.on_delegation_needed = self._delegate_task
            self.controllers[c.name] = ctrl

    async def _delegate_task(
        self,
        requester: Character,
        skill: str,
        required_level: int,
        item_code: str,
        quantity: int,
    ):
        capable = [
            name
            for name, c in self.characters.items()
            if name != requester.name
            and getattr(c.skills, skill).level >= required_level
            and self.controllers[name].todo_task is None
        ]

        if not capable:
            logger.warning(
                "Aucun perso disponible pour %s (skill %s lv.%d) — tâche abandonnée",
                item_code,
                skill,
                required_level,
            )
            ctrl = self.controllers.get(requester.name)
            fallback = getattr(ctrl.default_routine, "fallback_drop", None)
            if fallback:
                logger.info(
                    "%s — délégation impossible, fallback farm %s",
                    requester.name,
                    fallback,
                )
                await self.cmd_farm(requester.name, fallback)
            else:
                ctrl.default_routine = None
            return

        target = capable[0]
        routine = GatheringRoutine(
            drop_code=item_code,
            world=self.world,
            movement_service=self.movement_service,
            gathering_service=self.gathering_service,
            bank_service=self.bank_service,
            equipment_service=self.equipment_service,
            loadout_planner=self.loadout_planner,
        )
        self.controllers[target].set_todo(
            GoalTask(item_code=item_code, target_quantity=quantity, routine=routine)
        )
        logger.info(
            "Délégation : %s demande à %s de farmer %dx %s",
            requester.name,
            target,
            quantity,
            item_code,
        )

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
            bank_service=self.bank_service,
            equipment_service=self.equipment_service,
            loadout_planner=self.loadout_planner,
        )

        if qty is None:
            self.controllers[name].set_default(routine)
            logger.info("%s — farm %s en boucle", name, drop_code)
        else:
            self.controllers[name].set_todo(
                GoalTask(
                    item_code=drop_code,
                    target_quantity=qty,
                    routine=routine,
                )
            )
            logger.info("%s — farm %s jusqu'à %d", name, drop_code, qty)

    async def cmd_craft_routine(self, name: str, item_code: str):
        """Lance une CraftingRoutine en default — craft jusqu'à épuisement des ressources."""
        item = self.world.items.get(item_code)
        if item is None or item.craft is None:
            logger.warning("Item inconnu ou non craftable : %s", item_code)
            return

        routine = CraftingRoutine(
            item_code=item_code,
            bank_service=self.bank_service,
            craft_service=self.crafting_service,
            movement_service=self.movement_service,
            world=self.world,
        )
        self.controllers[name].set_default(routine)
        logger.info("%s — CraftingRoutine %s en default", name, item_code)

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
        self.controllers[name].set_todo(task)
        logger.info("%s — craft %dx %s", name, quantity, item.name)

    async def cmd_move(self, name: str, x: int, y: int):
        if name not in self.controllers:
            logger.warning("Perso inconnu : %s", name)
            return
        task = MoveToTask(x, y, self.movement_service)
        self.controllers[name].set_priority(task)
        logger.info("%s — déplacement vers (%d, %d)", name, x, y)

    async def cmd_fight(self, name: str, monster_code: str):
        if name not in self.controllers:
            logger.warning("Perso inconnu : %s", name)
            return

        tile = self.world.closest_monster_tile(
            monster_code,
            self.characters[name].position.x,
            self.characters[name].position.y,
        )
        if tile is None:
            logger.warning("Monstre inconnu : %s", monster_code)
            return

        routine = FightingRoutine(
            monster_code=monster_code,
            world=self.world,
            movement_service=self.movement_service,
            fighting_service=self.fighting_service,
            bank_service=self.bank_service,
            equipment_service=self.equipment_service,
            loadout_planner=self.loadout_planner,
        )
        self.controllers[name].set_default(routine)
        logger.info("%s — combat %s en boucle", name, monster_code)

    async def cmd_task(
        self,
        name: str,
        task_type: str | None = "items",
        fallback_drop: str | None = None,
    ):
        if name not in self.controllers:
            logger.warning("Perso inconnu : %s", name)
            return

        routine = TaskingRoutine(
            movement_service=self.movement_service,
            tasking_service=self.tasking_service,
            gathering_service=self.gathering_service,
            fighting_service=self.fighting_service,
            bank_service=self.bank_service,
            equipment_service=self.equipment_service,
            loadout_planner=self.loadout_planner,
            craft_service=self.crafting_service,
            world=self.world,
            task_type=task_type,
            fallback_drop=fallback_drop,
        )
        self.controllers[name].set_default(routine)
        logger.info("%s — TaskingRoutine (%s) en default", name, task_type or "auto")

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
            elif command == "fight":
                await self.cmd_fight(name, args[0])
            elif command == "task":
                task_type = args[0] if args else "items"
                fallback_drop = settings.get("fallback_args", [None])[0]
                await self.cmd_task(name, task_type, fallback_drop=fallback_drop)
            elif command == "stop":
                await self.cmd_stop(name)

            logger.info("%s — default chargé : %s %s", name, command, args)

    async def _controllers_loop(self):
        await asyncio.gather(*(c.main_loop() for c in self.controllers.values()))


def make_farm_condition(drop_code: str, qty: int):
    def condition(c):
        return c.inventory.count(drop_code) >= qty

    return condition
