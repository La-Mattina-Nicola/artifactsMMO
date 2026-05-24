from __future__ import annotations

from dataclasses import dataclass
from typing import List

from models import Monster


@dataclass
class SimulationAction:
    turn: int
    actor: str
    damage: int
    target_hp: int


@dataclass
class SimulationResult:
    turns: int
    player_won: bool
    player_hp: int
    monster_hp: int
    log: List[SimulationAction]


class CombatSimulator:
    def __init__(self, monster: Monster):
        self.monster = monster

    def simulate(
        self,
        player_stats: dict[str, int],
        include_log: bool = False,
        max_turns: int = 50,
    ) -> SimulationResult:
        player_hp = max(1, int(player_stats.get("max_hp", 0)))
        monster_hp = max(1, int(self.monster.hp))

        player_init = int(player_stats.get("initiative", 0))
        monster_init = int(self.monster.initiative)

        player_first = player_init > monster_init
        if player_init == monster_init:
            player_first = player_hp >= monster_hp

        player_damage = self._expected_damage_player(player_stats)
        monster_damage = self._expected_damage_monster(player_stats)

        log: List[SimulationAction] = []
        turn = 1

        while player_hp > 0 and monster_hp > 0 and turn <= max_turns:
            if player_first:
                monster_hp = max(0, monster_hp - player_damage)
                if include_log:
                    log.append(
                        SimulationAction(
                            turn=turn,
                            actor="player",
                            damage=player_damage,
                            target_hp=monster_hp,
                        )
                    )
                if monster_hp <= 0:
                    break

                player_hp = max(0, player_hp - monster_damage)
                if include_log:
                    log.append(
                        SimulationAction(
                            turn=turn,
                            actor="monster",
                            damage=monster_damage,
                            target_hp=player_hp,
                        )
                    )
            else:
                player_hp = max(0, player_hp - monster_damage)
                if include_log:
                    log.append(
                        SimulationAction(
                            turn=turn,
                            actor="monster",
                            damage=monster_damage,
                            target_hp=player_hp,
                        )
                    )
                if player_hp <= 0:
                    break

                monster_hp = max(0, monster_hp - player_damage)
                if include_log:
                    log.append(
                        SimulationAction(
                            turn=turn,
                            actor="player",
                            damage=player_damage,
                            target_hp=monster_hp,
                        )
                    )

            turn += 1

        return SimulationResult(
            turns=turn,
            player_won=monster_hp <= 0 and player_hp > 0,
            player_hp=player_hp,
            monster_hp=monster_hp,
            log=log,
        )

    def _expected_damage_player(self, stats: dict[str, int]) -> int:
        dmg_global = stats.get("dmg", 0)
        crit = stats.get("critical_strike", 0)

        total = 0
        total += self._element_damage(
            stats.get("attack_fire", 0),
            dmg_global,
            stats.get("dmg_fire", 0),
            self.monster.res_fire,
            crit,
        )
        total += self._element_damage(
            stats.get("attack_earth", 0),
            dmg_global,
            stats.get("dmg_earth", 0),
            self.monster.res_earth,
            crit,
        )
        total += self._element_damage(
            stats.get("attack_water", 0),
            dmg_global,
            stats.get("dmg_water", 0),
            self.monster.res_water,
            crit,
        )
        total += self._element_damage(
            stats.get("attack_air", 0),
            dmg_global,
            stats.get("dmg_air", 0),
            self.monster.res_air,
            crit,
        )
        return total

    def _expected_damage_monster(self, stats: dict[str, int]) -> int:
        crit = self.monster.critical_strike

        total = 0
        total += self._element_damage(
            self.monster.attack_fire,
            0,
            0,
            stats.get("res_fire", 0),
            crit,
        )
        total += self._element_damage(
            self.monster.attack_earth,
            0,
            0,
            stats.get("res_earth", 0),
            crit,
        )
        total += self._element_damage(
            self.monster.attack_water,
            0,
            0,
            stats.get("res_water", 0),
            crit,
        )
        total += self._element_damage(
            self.monster.attack_air,
            0,
            0,
            stats.get("res_air", 0),
            crit,
        )
        return total

    def _element_damage(
        self,
        base_attack: int,
        dmg_global: int,
        dmg_elem: int,
        resistance: int,
        critical_strike: int,
    ) -> int:
        if base_attack <= 0:
            return 0

        bonus = round(base_attack * ((dmg_global + dmg_elem) / 100))
        dmg_before_res = base_attack + bonus
        blocked = round(dmg_before_res * (resistance / 100))
        dmg_after_res = max(0, dmg_before_res - blocked)

        crit_chance = min(1.0, critical_strike / 100)
        expected = dmg_after_res * (1 + (0.5 * crit_chance))
        return int(round(expected))
