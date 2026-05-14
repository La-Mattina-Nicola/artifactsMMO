import asyncio
import logging
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.containers import FloatContainer, Float
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.widgets import Frame
from game import BotCompleter
from game.status_renderer import render_status_table
from services import MovementService, GatherService, CraftingService
from tasks import MoveToTask, GoalTask
from routines import GatheringRoutine
from data.nodes import NODES

logger = logging.getLogger(__name__)


class TextAreaHandler(logging.Handler):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def emit(self, record):
        msg = self.format(record)
        if self.manager.app:
            self.manager.app.loop.call_soon_threadsafe(lambda: self.manager.log(msg))


class GameManager:
    def __init__(self, characters, gateway):
        self.command_ready = asyncio.Event()
        kb = KeyBindings()

        self.log_handler = TextAreaHandler(self)
        self.log_handler.setFormatter(logging.Formatter("%(name)s — %(message)s"))

        # On ajoute le handler au logger racine ou aux loggers spécifiques
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        root_logger.setLevel(0)

        self.characters = {c.name: c for c in characters}
        self.gateway = gateway

        self.movement_service = MovementService(gateway)
        self.gathering_service = GatherService(gateway)
        self.crafting_service = CraftingService(gateway)

        from game import CharacterController

        self.controllers = {c.name: CharacterController(c) for c in characters}

        self._stop_event = asyncio.Event()

        self.log_area = TextArea(
            style="class:logs",
            scrollbar=True,
            wrap_lines=False,
            read_only=False,
        )

        self.status_control = FormattedTextControl(self._status_content)
        self.status_window = Window(
            content=FormattedTextControl(self._status_content),
            width=116,
            dont_extend_width=True,
        )

        self.input_buffer = Buffer(completer=BotCompleter(list(self.characters.keys())))

        # 2. Champ d'input simplifié
        self.input_field = TextArea(
            height=1,
            prompt="> ",
            multiline=False,
            wrap_lines=False,
            completer=BotCompleter(list(self.characters.keys())),
            accept_handler=self._on_input_accept,
            # Ces options sont vitales pour l'autocomplétion
            complete_while_typing=True,
            # On permet au menu de déborder du widget
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
        # 2. Construction du layout
        root = FloatContainer(
            content=body_layout,
            floats=[
                Float(
                    # Retire 'scrollbar=True' ici
                    content=CompletionsMenu(max_height=10),
                    xcursor=True,
                    ycursor=True,
                ),
            ],
        )

        # Nettoyage de la fin du __init__ de GameManager
        kb = KeyBindings()

        @kb.add("c-c")
        def _(event):
            self._stop_event.set()
            event.app.exit()

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
            style=ui_style,  # Applique bien le style ici
        )

        # handler pour les logs
        # Configurer le handler de log APRES avoir créé self.app
        handler = TextAreaHandler(self)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.DEBUG)

    def _setup_kb(self):
        kb = KeyBindings()

        @kb.add("c-c")
        def _(event):
            self._stop_event.set()
            event.app.exit()

        return kb

    def _on_input_accept(self, buffer):
        # Cette fonction est appelée quand tu appuies sur ENTER
        text = buffer.text.strip()
        if text:
            parts = text.split()
            cmd = parts[0]
            args = parts[1:]
            # On lance le dispatch sans bloquer l'UI
            asyncio.create_task(self._dispatch(cmd, args))

        # L'input est automatiquement vidé par le TextArea après accept_handler

    def _status_content(self):
        # Utilise ton status_renderer.py
        # Pour "agrandir" les personnages, assure-toi que ton renderer
        # ajoute plus de sauts de ligne ou d'infos par perso
        return render_status_table(self.characters)

    # ----------------------------------------------------------------------
    # STATUS PANEL CONTENT
    # ----------------------------------------------------------------------
    def _status_content(self):
        text = render_status_table(self.characters)
        return FormattedText([("", text)])

    # ----------------------------------------------------------------------
    # LOGGING
    # ----------------------------------------------------------------------
    def log(self, msg: str):
        # On ajoute le texte et on force le scroll vers le bas
        self.log_area.buffer.insert_text(msg + "\n")
        self.log_area.buffer.cursor_position = len(self.log_area.text)

    def _on_input_accept(self, buffer):
        text = buffer.text.strip()
        if text:
            parts = text.split()
            asyncio.create_task(self._dispatch(parts[0], parts[1:]))

    # ----------------------------------------------------------------------
    # COMMAND HANDLING
    # ----------------------------------------------------------------------
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
            self.log(f"Commande inconnue : '{command}'")

    async def _cmd_status(self, args):
        self.log("Status mis à jour (voir panneau à droite).")

    async def _cmd_help(self, args):
        self.log("Commandes disponibles :")
        self.log("  status                    — rafraîchit le panneau STATUS")
        self.log("  help                      — affiche cette aide")
        self.log("  quit                      — arrête le bot")
        self.log("  move <name> <x> <y>       — déplace un personnage")
        self.log("  farm <name> <node> [qty]  — commence à farm des ressources")
        self.log("  stop <name>               — arrête la tâche en cours")

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
            self.log("Usage : farm <name> <node> [qty]")
            return

        name = args[0]
        node_key = args[1]
        node = NODES.get(node_key)

        if not node:
            self.log(f"Node inconnu : {node_key}")
            return

        qty = int(args[2]) if len(args) == 3 else None

        if name not in self.controllers:
            self.log(f"Personnage inconnu : {name}")
            return

        controller = self.controllers[name]

        routine = GatheringRoutine(
            node=node,
            movement_service=self.movement_service,
            gathering_service=self.gathering_service,
        )

        if qty is None:
            controller.set_default(routine)
            self.log(f"{name} farm {node_key} en boucle")
        else:
            condition = make_goal_condition(node_key, qty)
            controller.set_todo(GoalTask(routine, condition))
            self.log(f"{name} farm {node_key} jusqu'à {qty}")

    async def _cmd_stop(self, args):
        if len(args) != 1:
            self.log("Usage : stop <name>")
            return

        name = args[0]
        if name not in self.controllers:
            self.log(f"Personnage inconnu : {name}")
            return

        c = self.controllers[name]
        c.priority_task = None
        c.todo_task = None
        c.default_routine = None

        self.log(f"{name} arrêté.")

    # ----------------------------------------------------------------------
    # MAIN LOOP
    # ----------------------------------------------------------------------
    async def _input_loop(self):
        while not self._stop_event.is_set():
            # Attend que ENTER soit pressé
            await self.command_ready.wait()
            self.command_ready.clear()

            text = self.input_buffer.text.strip()
            self.input_buffer.reset()

            if not text:
                continue

            parts = text.split()
            cmd = parts[0]
            args = parts[1:]

            await self._dispatch(cmd, args)

    async def _controllers_loop(self):
        await asyncio.gather(*(c.main_loop() for c in self.controllers.values()))

    async def start(self):
        with patch_stdout():
            await asyncio.gather(
                self.app.run_async(),
                self._input_loop(),
                self._controllers_loop(),
            )


# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------
def make_goal_condition(resource_drop: str, qty: int):
    def condition(character):
        return character.inventory.count(resource_drop) >= qty

    return condition
