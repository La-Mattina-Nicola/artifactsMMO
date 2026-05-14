# bot_completer.py

from prompt_toolkit.completion import Completer, Completion


class BotCompleter(Completer):
    def __init__(self, character_names: list[str]):
        self.character_names = character_names
        self.commands = {
            "status": [],
            "help": [],
            "quit": [],
            "move": character_names,
            "farm": character_names,
            "stop": character_names,
        }

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.split()

        if len(text) == 0 or (
            len(text) == 1 and not document.text_before_cursor.endswith(" ")
        ):
            word = text[0] if text else ""
            for cmd in self.commands:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))

        elif len(text) == 1 or (
            len(text) == 2 and not document.text_before_cursor.endswith(" ")
        ):
            cmd = text[0]
            word = text[1] if len(text) == 2 else ""
            for arg in self.commands.get(cmd, []):
                if arg.startswith(word):
                    yield Completion(arg, start_position=-len(word))
