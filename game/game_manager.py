import asyncio
import logging
from prompt_toolkit import PromptSession
from game import BotCompleter, CharacterController
from prompt_toolkit.patch_stdout import patch_stdout
from services import MovementService, GatherService, TaskService, CraftingService
from tasks import MoveToTask, GoalTask
from routines import GatheringRoutine

logger = logging.getLogger(__name__)

COMMANDS = ["status", "help", "quit"]


class GameManager:
    def __init__(self, characters, gateway):
        self.characters = {c.name: c for c in characters}

        # Services
        self.movement_service = MovementService(gateway)
        self.gathering_service = GatherService(gateway)
        self.crafting_service = CraftingService(gateway)

        self.task_service = TaskService(
            movement=self.movement_service,
            gathering=self.gathering_service,
            crafting=self.crafting_service,
        )

        # Controllers
        self.controllers = {
            c.name: CharacterController(c, self.task_service) for c in characters
        }

    async def handle_commands(self, session: PromptSession):
        while not self._stop_event.is_set():
            try:
                raw = await session.prompt_async("> ")
                parts = raw.strip().split()
                if not parts:
                    continue
                await self._dispatch(parts[0], parts[1:])
            except (EOFError, KeyboardInterrupt):
                self._stop_event.set()
                break

    async def _dispatch(self, command: str, args: list[str]):
        handlers = {
            "status": self._cmd_status,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "move": self._cmd_move,
            "farm": self._cmd_farm,
            "stop": self._cmd_stop,
        }
        handler = handlers.get(command)
        if handler:
            await handler(args)
        else:
            print(f"Commande inconnue : '{command}'. Tape 'help' pour la liste.")

    async def _cmd_status(self, args):
        print(f"{'Nom':<15} {'Lvl':>4} {'HP':>8} {'Position':>12} {'Cooldown':>10}")
        print("-" * 55)
        for c in self.characters.values():
            pos = f"({c.position.x}, {c.position.y})"
            hp = f"{c.stats.hp}/{c.stats.max_hp}"
            print(
                f"{c.name:<15} {c.level:>4} {hp:>8} {pos:>12} {c.cooldowns.value:>9}s"
            )

    async def _cmd_help(self, args):
        print("Commandes disponibles :")
        print("  status        — affiche l'état des personnages")
        print("  help          — affiche cette aide")
        print("  quit          — arrête le bot")

    async def _cmd_quit(self, args):
        print("Arrêt...")
        self._stop_event.set()

    async def _monitoring_loop(self):
        while not self._stop_event.is_set():
            await asyncio.sleep(5)
            logger.debug(
                "Monitoring tick — %d personnages actifs", len(self.characters)
            )

    async def start(self):
        self._stop_event = asyncio.Event()
        completer = BotCompleter(list(self.characters.keys()))
        session = PromptSession(completer=completer)
        with patch_stdout():
            try:
                await asyncio.gather(
                    self.handle_commands(session),
                    self._monitoring_loop(),
                    *[c.main_loop() for c in self.controllers.values()],
                )
            except asyncio.CancelledError:
                pass

    async def _cmd_move(self, args):
        if len(args) != 3:
            print("Usage : move <name> <x> <y>")
            return
        name, x, y = args[0], int(args[1]), int(args[2])
        if name not in self.characters:
            print(f"Personnage inconnu : '{name}'")
            return
        task = MoveToTask(x, y, self.movement_service)
        self.controllers[name].set_priority(task)
        print(f"{name} se déplace vers ({x}, {y})")

    async def _cmd_farm(self, args):
        if len(args) < 2:
            print("Usage : farm <name> <node> [qty]")
            return

        name = args[0]
        node = args[1]
        qty = int(args[2]) if len(args) == 3 else None

        if name not in self.controllers:
            print(f"Personnage inconnu : {name}")
            return

        controller = self.controllers[name]

        routine = GatheringRoutine(
            node=node,
            movement_service=self.movement_service,
            gathering_service=self.gathering_service,
        )

        if qty is None:
            controller.set_default(routine)
            print(f"{name} farm {node} en boucle")
        else:
            condition = make_goal_condition(node, qty)  
            controller.set_todo(GoalTask(routine, condition))
            print(f"{name} farm {node} jusqu'à {qty}")

    async def _cmd_stop(self, args):
        if len(args) != 1:
            print("Usage : stop <name>")
            return

        name = args[0]
        if name not in self.controllers:
            print(f"Personnage inconnu : {name}")
            return

        c = self.controllers[name]
        c.priority_task = None
        c.todo_task = None
        c.default_routine = None

        print(f"{name} arrêté.")

def make_goal_condition(node: str, qty: int):
    def condition(character):
        return character.inventory.count(node) >= qty
    return condition
