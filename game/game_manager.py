import asyncio
import logging
from game.bot_completer import BotCompleter
from game.base_manager import BaseManager
from game.status_renderer import render_status_table
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.containers import FloatContainer, Float
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.widgets import Frame
from data.world import World
from tasks import MoveToTask, GoalTask
from routines import GatheringRoutine, FightingRoutine
from tasks.craft_task import CraftTask

logger = logging.getLogger(__name__)

MAX_LOG_LINES = 500


class TextAreaHandler(logging.Handler):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self._pending = 0
        self.MAX_PENDING = 50  # max messages en attente

    def emit(self, record):
        if self._pending >= self.MAX_PENDING:
            return  # drop le message si trop de backlog
        msg = self.format(record)
        if self.manager.app and self.manager.app.loop:
            self._pending += 1

            def _log():
                self._pending -= 1
                self.manager.log(msg)

            self.manager.app.loop.call_soon_threadsafe(_log)


class GameManager(BaseManager):
    def __init__(self, characters, gateway, world: "World", bank_service):
        super().__init__(characters, gateway, world, bank_service)

        self.log_handler = TextAreaHandler(self)
        self.log_handler.setFormatter(logging.Formatter("%(name)s — %(message)s"))
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        root_logger.setLevel(logging.WARNING)  # LEVEL LOGGING

        self._completer = BotCompleter(
            list(self.characters.keys()),
            [drop.code for r in self.world.resources.values() for drop in r.drops],
            [code for code, item in self.world.items.items() if item.craft is not None],
            [m.code for m in self.world.monsters.values()],
        )

        self._stop_event = asyncio.Event()

        self.log_area = TextArea(
            style="class:logs",
            scrollbar=True,
            wrap_lines=False,
            read_only=False,
        )
        self.status_control = FormattedTextControl(self._status_content)
        self.status_window = Window(
            content=FormattedTextControl(
                self._status_content,
                focusable=False,
            ),
            width=116,
            dont_extend_width=True,
        )
        self.input_buffer = Buffer(completer=self._completer)
        self.input_field = TextArea(
            height=1,
            prompt="> ",
            multiline=False,
            wrap_lines=False,
            completer=self._completer,
            accept_handler=self._on_input_accept,
            complete_while_typing=True,
        )
        body_layout = HSplit(
            [
                VSplit(
                    [
                        Frame(self.log_area, title="Logs"),
                        Frame(self.status_window, title="Heroes"),
                    ]
                ),
                self.input_field,
            ]
        )
        root = FloatContainer(
            content=body_layout,
            floats=[
                Float(
                    content=CompletionsMenu(max_height=10),
                    xcursor=True,
                    ycursor=True,
                ),
            ],
        )

        kb = KeyBindings()

        self.focus_input = True

        @kb.add("c-l")  # Ctrl+L → focus logs
        def _(event):
            if self.focus_input:
                event.app.layout.focus(self.log_area)
                self.focus_input = False
            else:
                event.app.layout.focus(self.input_field)
                self.focus_input = True

        ui_style = Style.from_dict(
            {
                "completion-menu": "bg:#222222 #ffffff",
                "completion-menu.completion.current": "bg:#222222 #28cddc",
                "completion-menu.completion": "bg:#222222 #ffffff",
                "frame.label": "#ffffff bold",
            }
        )

        self.app = Application(
            layout=Layout(root, focused_element=self.input_field),
            key_bindings=kb,
            full_screen=True,
            refresh_interval=0.5,
            style=ui_style,
            mouse_support=True,
        )

    def _setup_kb(self):
        kb = KeyBindings()

        @kb.add("c-c")
        def _(event):
            self._stop_event.set()
            event.app.exit()

        return kb

    def _on_input_accept(self, buffer):
        text = buffer.text.strip()
        if text:
            parts = text.split()
            asyncio.create_task(self._dispatch(parts[0], parts[1:]))

    def _status_content(self):
        text = render_status_table(self.characters)
        return FormattedText([("", text)])

    def log(self, msg: str):
        self.log_area.buffer.insert_text(msg + "\n")

        lines = self.log_area.text.split("\n")
        if len(lines) > MAX_LOG_LINES:
            from prompt_toolkit.document import Document

            trimmed = "\n".join(lines[-MAX_LOG_LINES:])
            self.log_area.buffer.set_document(Document(trimmed), bypass_readonly=True)

        self.log_area.buffer.cursor_position = len(self.log_area.text)

    async def _dispatch(self, command: str, args: list[str]):
        handlers = {
            "status": self._cmd_status,
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "move": self._cmd_move,
            "farm": self._cmd_farm,
            "craft": self._cmd_craft,
            "fight": self._cmd_fight,
            "task": self._cmd_task,
            "bank": self._cmd_bank,
            "stop": self._cmd_stop,
        }
        handler = handlers.get(command)
        if handler:
            await handler(args)
        else:
            self.log(f"Commande inconnue : '{command}'")

    async def _cmd_status(self, args):
        self.log("Status mis à jour (voir panneau à droite).")

    async def _cmd_help(self, args):
        self.log("Commandes disponibles :")
        self.log("  help                      — affiche cette aide")
        self.log("  status                    — rafraîchit le panneau STATUS")
        self.log("  bank                      — effectue un dépôt complet à la banque")
        self.log("  move <name> <x> <y>       — déplace un personnage")
        self.log("  farm <name> <node> [qty]  — commence à farm des ressources")
        self.log("  craft <name> <item> <qty> — craft un item depuis la banque")
        self.log("  stop <name>               — arrête la tâche en cours")
        self.log("  quit                      — arrête le bot")

    async def _cmd_quit(self, args):
        self.log("Arrêt demandé…")
        self._stop_event.set()
        self.app.exit()

    async def _cmd_move(self, args):
        if len(args) != 3:
            self.log("Usage : move <name> <x> <y>")
            return

        name, x, y = args[0], int(args[1]), int(args[2])

        if name not in self.characters:
            self.log(f"Personnage inconnu : '{name}'")
            return

        task = MoveToTask(x, y, self.movement_service)
        self.controllers[name].set_priority(task)
        self.log(f"{name} se déplace vers ({x}, {y})")

    async def _cmd_farm(self, args):
        if len(args) < 2:
            self.log("Usage : farm <name> <drop> [qty]")
            return

        name = args[0]
        drop_code = args[1]
        qty = int(args[2]) if len(args) == 3 else None

        if name not in self.controllers:
            self.log(f"Personnage inconnu : {name}")
            return

        character = self.characters[name]
        node = self.world.closest_node(
            drop_code, character.position.x, character.position.y
        )
        if node is None:
            self.log(f"Ressource inconnue : {drop_code}")
            return

        controller = self.controllers[name]
        routine = GatheringRoutine(
            drop_code=drop_code,
            world=self.world,
            movement_service=self.movement_service,
            gathering_service=self.gathering_service,
        )

        if qty is None:
            controller.set_default(routine)
            self.log(f"🎯 — {name:<10} farm {drop_code:<20} en boucle")
        else:
            self.controllers[name].set_todo(
                GoalTask(
                    item_code=drop_code,
                    target_quantity=qty,
                    routine=routine,
                )
            )
            self.log(f"{name:<10} farm {drop_code:<20} jusqu'à {qty}")

    async def _cmd_stop(self, args):
        if len(args) != 1:
            self.log("Usage : stop <name>")
            return

        name = args[0]
        if name not in self.controllers:
            self.log(f"Personnage inconnu : {name}")
            return

        c = self.controllers[name]
        c.priority_task = []
        c.todo_task = None
        c.default_routine = None

        self.log(f"{name} arrêté.")

    async def _cmd_bank(self, args):
        await self.bank_service.load()
        if not self.bank_service.items:
            self.log("Banque vide ou non chargée.")
            return

        self.log(f"{'Item':<30} {'Quantité':>10}")
        self.log("-" * 42)
        for code, qty in sorted(
            self.bank_service.items.items(), key=lambda x: x[1], reverse=False
        ):
            self.log(f"{code:<30} {qty:>10}")

    async def _cmd_craft(self, args):
        if len(args) == 2:
            # Sans qty → CraftingRoutine en default
            if args[0] not in self.controllers:
                self.log(f"Personnage inconnu : {args[0]}")
                return
            await self.cmd_craft_routine(args[0], args[1])
            self.log(f"{args[0]} craft {args[1]} en boucle")

        elif len(args) == 3:
            # Avec qty → CraftTask en todo
            if args[0] not in self.controllers:
                self.log(f"Personnage inconnu : {args[0]}")
                return
            await self.cmd_craft(args[0], args[1], int(args[2]))
            self.log(f"{args[0]} craft {args[2]}x {args[1]}")

        else:
            self.log("Usage : craft <name> <item> [qty]")

    async def _cmd_fight(self, args: list):
        if len(args) < 2:
            self.log("Usage : fight <name> <monster_code>")
            return

        name = args[0]
        monster_code = args[1]

        if name not in self.controllers:
            self.log(f"Personnage inconnu : {name}")
            return

        character = self.characters[name]
        tile = self.world.closest_monster_tile(
            monster_code, character.position.x, character.position.y
        )
        if tile is None:
            self.log(f"Monstre inconnu : {monster_code}")
            return

        controller = self.controllers[name]
        routine = FightingRoutine(
            monster_code=monster_code,
            world=self.world,
            movement_service=self.movement_service,
            fighting_service=self.fighting_service,
        )
        controller.set_default(routine)
        self.log(f"{name} combat {monster_code} en boucle")

    async def _cmd_task(self, args):
        if len(args) < 1 or len(args) > 2:
            self.log("Usage : task <name> [items|monsters]")
            return
        name = args[0]
        task_type = args[1] if len(args) == 2 else None

        if name not in self.controllers:
            self.log(f"Personnage inconnu : {name}")
            return

        await self.cmd_task(name, task_type)
        self.log(f"{name} — TaskingRoutine ({task_type or 'auto'}) en default")

    async def _controllers_loop(self):
        await asyncio.gather(*(c.main_loop() for c in self.controllers.values()))

    async def start(self):
        asyncio.create_task(self._startup())
        await asyncio.gather(
            self.app.run_async(),
            self._controllers_loop(),
        )

    async def _startup(self):
        await asyncio.sleep(1)
        await self.load_defaults()


def make_goal_condition(resource_drop: str, qty: int):
    def condition(character):
        return character.inventory.count(resource_drop) >= qty

    return condition
