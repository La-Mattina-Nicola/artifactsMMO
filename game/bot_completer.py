from prompt_toolkit.completion import Completer, Completion


class BotCompleter(Completer):
    def __init__(self, character_names: list[str], drop_codes: list[str]):
        self.character_names = character_names
        self.commands = {
            "status": [],
            "help": [],
            "quit": [],
            "move": character_names,
            "farm": character_names,
            "stop": character_names,
        }
        self.farm_drops = drop_codes

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

        elif len(text) == 2 or (
            len(text) == 3 and not document.text_before_cursor.endswith(" ")
        ):
            cmd = text[0]
            word = text[2] if len(text) == 3 else ""
            if cmd == "farm":
                for drop in self.farm_drops:
                    if drop.startswith(word):
                        yield Completion(drop, start_position=-len(word))
