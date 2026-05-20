from data.world import World
from routines.routine import Routine
from tasks.fight_task import FighterTask
from tasks.move_task import MoveToTask


class FightingRoutine(Routine):
    def __init__(
        self, monster_code, world: "World", movement_service, fighting_service
    ):
        self.monster_code = monster_code
        self.world = world
        self.movement_service = movement_service
        self.fighting_service = fighting_service

    def generate_task(self, character):
        monster_tile = self.world.closest_monster_tile(
            self.monster_code, character.position.x, character.position.y
        )
        if monster_tile is None:
            raise ValueError(f"Monstre introuvable : {self.monster_code}")

        if (
            character.position.x != monster_tile.x
            or character.position.y != monster_tile.y
            or character.position.layer != monster_tile.layer
        ):
            return MoveToTask(
                monster_tile.x,
                monster_tile.y,
                self.movement_service,
                layer=monster_tile.layer,
            )

        return FighterTask(monster_tile, self.fighting_service)
