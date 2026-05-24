from __future__ import annotations

from collections import defaultdict

from data.world import World
from models import Character, Item, Monster

from services.banking import BankService
from services.combat_simulator import CombatSimulator, SimulationResult
from models.loadout import LoadoutPlan
from services.equipment_constants import (
    SLOT_TYPES,
    FIGHT_SLOTS,
    GATHER_SLOTS,
    STAT_FIELDS,
    DEFAULT_FIGHT_WEIGHTS,
    DEFAULT_GATHER_WEIGHTS,
)


class LoadoutPlanner:
    def __init__(
        self,
        world: World,
        bank_service: BankService,
        fight_weights: dict[str, float] | None = None,
        gather_weights: dict[str, float] | None = None,
        top_n: int = 8,
        beam_width: int = 30,
    ):
        self.world = world
        self.bank_service = bank_service
        self.fight_weights = fight_weights or DEFAULT_FIGHT_WEIGHTS
        self.gather_weights = gather_weights or DEFAULT_GATHER_WEIGHTS
        self.top_n = top_n
        self.beam_width = beam_width
        self._item_stats_cache: dict[str, dict[str, int]] = {}

    def plan_fight(
        self,
        character: Character,
        monster_code: str,
        food_min: int = 2,
        food_target: int | None = None,
        ignore_inventory_food: bool = False,
    ) -> LoadoutPlan:
        monster = self.world.monsters.get(monster_code)
        if not monster:
            return LoadoutPlan(equip_changes={}, withdraw_items={})

        base_stats = self._base_stats(character)
        available_counts = self._available_counts(character)

        weapon = self._best_weapon(character, base_stats, monster, available_counts)
        desired_slots = {"weapon": weapon} if weapon else {}

        desired_slots.update(
            self._best_fight_gear(
                character, base_stats, monster, available_counts, weapon
            )
        )

        target = food_target if food_target is not None else food_min
        return self._build_plan(
            character,
            desired_slots,
            available_counts,
            target,
            ignore_inventory_food,
        )

    def plan_gather(self, character: Character, drop_code: str) -> LoadoutPlan:
        resource = self._resource_for_drop(drop_code)
        if not resource:
            return LoadoutPlan(equip_changes={}, withdraw_items={})

        available_counts = self._available_counts(character)
        desired_slots = {}

        tool = self._best_tool(character, resource.skill, available_counts)
        if not tool:
            weapon_candidates = self._slot_candidates(
                "weapon", character, available_counts
            )
            weapon_candidates.sort(
                key=lambda code: self._gather_item_score(self.world.items[code]),
                reverse=True,
            )
            tool = weapon_candidates[0] if weapon_candidates else None
        if tool:
            desired_slots["weapon"] = tool

        used_counts: dict[str, int] = defaultdict(int)
        if tool:
            used_counts[tool] += 1

        for slot in GATHER_SLOTS:
            if slot == "weapon":
                continue
            candidates = self._slot_candidates(slot, character, available_counts)
            candidates.sort(
                key=lambda code: self._gather_item_score(self.world.items[code]),
                reverse=True,
            )
            selected = self._pick_first_available(
                candidates, available_counts, used_counts
            )
            if selected:
                desired_slots[slot] = selected

        return self._build_plan(
            character, desired_slots, available_counts, food_target=0
        )

    def _build_plan(
        self,
        character: Character,
        desired_slots: dict[str, str],
        available_counts: dict[str, int],
        food_target: int,
        ignore_inventory_food: bool = False,
    ) -> LoadoutPlan:
        current_equipment = self._current_equipment(character)

        inventory_counts = self._inventory_counts(character)
        equipped_counts = self._equipped_counts(character)

        equip_changes: dict[str, str] = {}
        for slot, code in desired_slots.items():
            if not code:
                continue
            if current_equipment.get(slot) == code:
                continue

            if equipped_counts.get(code, 0) > 0:
                continue

            equip_changes[slot] = code

        desired_counts: dict[str, int] = defaultdict(int)
        for code in equip_changes.values():
            desired_counts[code] += 1
        withdraw_items: dict[str, int] = {}

        for code, desired in desired_counts.items():
            owned = inventory_counts.get(code, 0) + equipped_counts.get(code, 0)
            needed = max(0, desired - owned)
            if needed > 0:
                withdraw_items[code] = needed

        food_code, food_needed = self._food_plan(
            character, food_target, ignore_inventory_food=ignore_inventory_food
        )
        if food_code and food_needed > 0:
            withdraw_items[food_code] = withdraw_items.get(food_code, 0) + food_needed

        return LoadoutPlan(
            equip_changes=equip_changes,
            withdraw_items=withdraw_items,
            food_code=food_code,
            food_needed=food_needed,
        )

    def _food_plan(
        self,
        character: Character,
        food_target: int,
        ignore_inventory_food: bool = False,
    ) -> tuple[str | None, int]:
        if food_target <= 0:
            return None, 0

        inventory_counts = self._inventory_counts(character)
        bank_counts = self.bank_service.items
        best_code = None
        best_heal = 0

        for code, item in self.world.items.items():
            if not item.is_food():
                continue
            if inventory_counts.get(code, 0) <= 0 and bank_counts.get(code, 0) <= 0:
                continue
            heal = item.heal_value()
            if heal > best_heal:
                best_heal = heal
                best_code = code

        if not best_code:
            return None, 0

        bank_qty = bank_counts.get(best_code, 0)
        current_food = 0
        if not ignore_inventory_food:
            current_food = inventory_counts.get(best_code, 0)
        needed = max(0, food_target - current_food)
        return best_code, min(needed, bank_qty)

    def _best_weapon(
        self,
        character: Character,
        base_stats: dict[str, int],
        monster: Monster,
        available_counts: dict[str, int],
    ) -> str | None:
        candidates = self._slot_candidates("weapon", character, available_counts)
        if not candidates:
            return None

        best_code = None
        best_score = float("-inf")
        simulator = CombatSimulator(monster)

        for code in candidates:
            item = self.world.items.get(code)
            if not item:
                continue
            stats = self._apply_item_to_stats(base_stats, item)
            result = simulator.simulate(stats, include_log=False)
            score = self._score_simulation(result)
            if score > best_score:
                best_score = score
                best_code = code

        return best_code

    def _best_fight_gear(
        self,
        character: Character,
        base_stats: dict[str, int],
        monster: Monster,
        available_counts: dict[str, int],
        weapon: str | None,
    ) -> dict[str, str]:
        candidates_by_slot: dict[str, list[str]] = {}
        item_scores: dict[str, float] = {}

        for slot in FIGHT_SLOTS:
            if slot == "weapon":
                continue
            candidates = self._slot_candidates(slot, character, available_counts)
            if not candidates:
                continue
            for code in candidates:
                if code not in item_scores:
                    item_scores[code] = self._fight_item_score(
                        self.world.items[code], monster
                    )
            candidates.sort(key=lambda c: item_scores[c], reverse=True)
            candidates_by_slot[slot] = candidates[: self.top_n]

        if not candidates_by_slot:
            return {}

        builds = [({}, 0.0, defaultdict(int))]
        for slot, candidates in candidates_by_slot.items():
            new_builds = []
            for selection, score, counts in builds:
                for code in [None, *candidates]:
                    if code is None:
                        new_builds.append(
                            (selection.copy(), score, defaultdict(int, counts))
                        )
                        continue
                    if counts[code] + 1 > available_counts.get(code, 0):
                        continue
                    new_selection = selection.copy()
                    new_selection[slot] = code
                    new_counts = defaultdict(int, counts)
                    new_counts[code] += 1
                    new_score = score + item_scores[code]
                    new_builds.append((new_selection, new_score, new_counts))

            new_builds.sort(key=lambda b: b[1], reverse=True)
            builds = new_builds[: self.beam_width]

        best_selection = {}
        best_score = float("-inf")

        for selection, _, _ in builds:
            stats = base_stats.copy()
            if weapon and weapon in self.world.items:
                stats = self._apply_item_to_stats(stats, self.world.items[weapon])
            for code in selection.values():
                if code:
                    stats = self._apply_item_to_stats(stats, self.world.items[code])

            simulator = CombatSimulator(monster)
            result = simulator.simulate(stats, include_log=False)
            score = self._score_simulation(result)
            if score > best_score:
                best_score = score
                best_selection = selection

        return best_selection

    def _best_tool(
        self,
        character: Character,
        skill: str,
        available_counts: dict[str, int],
    ) -> str | None:
        candidates = [
            code
            for code, item in self.world.items.items()
            if item.type == "weapon"
            and item.is_tool_for(skill)
            and item.can_equip(character)
            and available_counts.get(code, 0) > 0
        ]
        if not candidates:
            return None

        return max(
            candidates,
            key=lambda code: self.world.items[code].tool_bonus(skill),
        )

    def _slot_candidates(
        self,
        slot: str,
        character: Character,
        available_counts: dict[str, int],
    ) -> list[str]:
        slot_type = SLOT_TYPES.get(slot)
        if not slot_type:
            return []

        return [
            code
            for code, item in self.world.items.items()
            if item.type == slot_type
            and item.can_equip(character)
            and available_counts.get(code, 0) > 0
        ]

    def _resource_for_drop(self, drop_code: str):
        for resource in self.world.resources.values():
            if any(drop.code == drop_code for drop in resource.drops):
                return resource
        return None

    def _current_equipment(self, character: Character) -> dict[str, str]:
        return {
            "weapon": character.equipment.weapon,
            "rune": character.equipment.rune,
            "shield": character.equipment.shield,
            "helmet": character.equipment.helmet,
            "body_armor": character.equipment.body_armor,
            "leg_armor": character.equipment.leg_armor,
            "boots": character.equipment.boots,
            "ring1": character.equipment.ring1,
            "ring2": character.equipment.ring2,
            "amulet": character.equipment.amulet,
            "artifact1": character.equipment.artifact1,
            "artifact2": character.equipment.artifact2,
            "artifact3": character.equipment.artifact3,
            "bag": character.equipment.bag,
        }

    def _inventory_counts(self, character: Character) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for item in character.inventory.items:
            counts[item.code] += item.quantity
        return counts

    def _equipped_counts(self, character: Character) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for code in self._current_equipment(character).values():
            if code:
                counts[code] += 1
        return counts

    def _available_counts(self, character: Character) -> dict[str, int]:
        counts = self._inventory_counts(character)
        for code, qty in self.bank_service.items.items():
            counts[code] += qty
        for code, qty in self._equipped_counts(character).items():
            counts[code] += qty
        return counts

    def _base_stats(self, character: Character) -> dict[str, int]:
        stats = {field: getattr(character.stats, field) for field in STAT_FIELDS}
        stats["hp"] = stats.get("max_hp", stats.get("hp", 0))
        for code in self._current_equipment(character).values():
            if not code:
                continue
            item = self.world.items.get(code)
            if item:
                stats = self._apply_item_to_stats(stats, item, sign=-1)
        return stats

    def _apply_item_to_stats(
        self, stats: dict[str, int], item: Item, sign: int = 1
    ) -> dict[str, int]:
        updated = stats.copy()
        for effect in item.effects:
            code = effect.code
            if code == "hp":
                updated["hp"] = updated.get("hp", 0) + (effect.value * sign)
                updated["max_hp"] = updated.get("max_hp", 0) + (effect.value * sign)
                continue
            if code in updated:
                updated[code] = updated.get(code, 0) + (effect.value * sign)
        return updated

    def _fight_item_score(self, item: Item, monster: Monster) -> float:
        weights = self.fight_weights
        score = 0.0

        attack_total = (
            monster.attack_fire
            + monster.attack_earth
            + monster.attack_water
            + monster.attack_air
        )
        if attack_total <= 0:
            attack_total = 1

        res_weights = {
            "res_fire": monster.attack_fire / attack_total,
            "res_earth": monster.attack_earth / attack_total,
            "res_water": monster.attack_water / attack_total,
            "res_air": monster.attack_air / attack_total,
        }

        for effect in item.effects:
            if effect.code == "hp":
                score += effect.value * weights.get("hp", 0)
                continue
            if effect.code == "critical_strike":
                score += effect.value * weights.get("crit", 0)
                continue
            if effect.code == "initiative":
                score += effect.value * weights.get("init", 0)
                continue
            if effect.code.startswith("res_"):
                score += (
                    effect.value
                    * weights.get("res", 0)
                    * res_weights.get(effect.code, 0)
                )
                continue
            if effect.code == "dmg":
                score += effect.value * weights.get("dmg", 0)
                continue
            if effect.code.startswith("dmg_"):
                score += effect.value * weights.get("dmg", 0)
                continue
            if effect.code.startswith("attack_"):
                score += effect.value * weights.get("attack", 0)
                continue

        return score

    def _gather_item_score(self, item: Item) -> float:
        weights = self.gather_weights
        score = 0.0
        for effect in item.effects:
            if effect.code == "hp":
                score += effect.value * weights.get("hp", 0)
                continue
            if effect.code.startswith("res_"):
                score += effect.value * weights.get("res", 0)
                continue
            if effect.code == "wisdom":
                score += effect.value * weights.get("wisdom", 0)
                continue
        return score

    def _pick_first_available(
        self,
        candidates: list[str],
        available_counts: dict[str, int],
        used_counts: dict[str, int],
    ) -> str | None:
        for code in candidates:
            if used_counts.get(code, 0) < available_counts.get(code, 0):
                used_counts[code] = used_counts.get(code, 0) + 1
                return code
        return None

    def _score_simulation(self, result: SimulationResult) -> float:
        if result.player_won:
            return 100000 + result.player_hp - (result.turns * 5)
        return -100000 - result.monster_hp - (result.turns * 5)
