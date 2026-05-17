def color(text, c=None):
    return f"{text}"


def percent(xp, max_xp):
    if max_xp <= 0:
        return "0.0%"
    return f"{(xp / max_xp) * 100:4.1f}%"


def cooldown_bar(character, width=9):
    total = character.cooldowns.value
    remaining = character.cooldown_remaining

    if total <= 0:
        filled = width
    else:
        filled = int(width * (remaining / total))

    empty = width - filled
    bar = f"{'█' * filled}{' ' * empty}"
    return f"{bar} {remaining:<3} s"
