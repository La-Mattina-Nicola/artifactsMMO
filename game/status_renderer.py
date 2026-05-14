# status_renderer.py
from models.character import Character
from game.ui_utils import percent, cooldown_bar


def render_status_table(characters: dict[str, "Character"]) -> str:
    chars = list(characters.values())
    COL = 18

    def col(text):
        return f"{text:>{COL}}"

    lines = []
    lines.append("")

    row = f"{'Nom/Lvl':<12}: "
    row += " | ".join(col(f"{c.name:<10}   lv.{c.level}") for c in chars)
    lines.append(row)

    row = f"{'HP & POS':<12}: "
    row += " | ".join(
        col(f"{c.stats.hp}/{c.stats.max_hp:<7} [{c.position.x},{c.position.y}]")
        for c in chars
    )
    lines.append(row)

    row = f"{'Task ':<12}: "
    row += " | ".join(
        col(f"{c.task}") for c in chars if c.task and c.task.type != "idle"
    )
    lines.append(row)

    row = f"{'Cooldown':<12}: "
    row += " | ".join(col(cooldown_bar(c)) for c in chars)
    lines.append(row)

    lines.append("")
    lines.append("-" * 53 + " METIERS " + "-" * 53)

    professions = [
        ("⛏️", lambda c: c.skills.mining),
        ("🪓", lambda c: c.skills.woodcutting),
        ("🎣", lambda c: c.skills.fishing),
        ("🗡️", lambda c: c.skills.weaponcrafting),
        ("🔨", lambda c: c.skills.gearcrafting),
        ("💎", lambda c: c.skills.jewelrycrafting),
        ("🍳", lambda c: c.skills.cooking),
        ("⚗️", lambda c: c.skills.alchemy),
    ]

    for label, getter in professions:
        label_title = ""
        if label == "⛏️" or label == "🗡️" or label == "⚗️":
            label_title = f"{label:<13}"
        else:
            label_title = f"{label:<11}"
        row = f"{label_title}: "

        row += " | ".join(
            col(
                f"lv.{getter(c).level:<3}{' ' * 6}{percent(getter(c).xp, getter(c).max_xp)} "
            )
            for c in chars
        )
        lines.append(row)

    return "\n".join(lines)
