SLOT_TYPES: dict[str, str] = {
    "weapon": "weapon",
    "rune": "rune",
    "shield": "shield",
    "helmet": "helmet",
    "body_armor": "body_armor",
    "leg_armor": "leg_armor",
    "boots": "boots",
    "ring1": "ring",
    "ring2": "ring",
    "amulet": "amulet",
    "artifact1": "artifact",
    "artifact2": "artifact",
    "artifact3": "artifact",
    "bag": "bag",
}

FIGHT_SLOTS = [
    "weapon",
    "helmet",
    "body_armor",
    "leg_armor",
    "boots",
    "shield",
    "rune",
    "amulet",
    "ring1",
    "ring2",
    "artifact1",
    "artifact2",
    "artifact3",
]

GATHER_SLOTS = [
    "weapon",
    "helmet",
    "body_armor",
    "leg_armor",
    "boots",
    "shield",
    "rune",
    "amulet",
    "ring1",
    "ring2",
    "artifact1",
    "artifact2",
    "artifact3",
]

STAT_FIELDS = {
    "hp",
    "max_hp",
    "haste",
    "critical_strike",
    "wisdom",
    "initiative",
    "attack_fire",
    "attack_earth",
    "attack_water",
    "attack_air",
    "dmg",
    "dmg_fire",
    "dmg_earth",
    "dmg_water",
    "dmg_air",
    "res_fire",
    "res_earth",
    "res_water",
    "res_air",
}

DEFAULT_FIGHT_WEIGHTS = {
    "hp": 1.0,
    "res": 1.4,
    "dmg": 0.8,
    "attack": 0.9,
    "crit": 0.6,
    "init": 0.2,
}

DEFAULT_GATHER_WEIGHTS = {
    "wisdom": 1.0,
    "hp": 0.2,
    "res": 0.1,
}
