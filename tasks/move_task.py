from models import Character
from tasks.base_task import Task
from services.movement import MovementService


class MoveToTask(Task):
    def __init__(self, x: int, y: int, movement_service, layer: str = "overworld"):
        self.x = x
        self.y = y
        self.layer = layer
        self.movement_service = movement_service
        self._step = 0

    async def execute_step(self, character) -> bool:
        # Déjà à destination
        if (
            character.position.x == self.x
            and character.position.y == self.y
            and character.position.layer == self.layer
        ):
            return True

        # Même layer → move direct
        if character.position.layer == self.layer:
            await self.movement_service.move(character, self.x, self.y)
            return True

        # Layer différent → transition
        if self._step == 0:
            tile = self.movement_service.find_transition(
                character.position.x,
                character.position.y,
                character.position.layer,
                self.layer,
            )
            if tile is None:
                raise ValueError(
                    f"Aucune transition vers {self.layer} depuis {character.position.layer}"
                )
            if character.position.x != tile.x or character.position.y != tile.y:
                await self.movement_service.move(character, tile.x, tile.y)
                return False
            self._step = 1
            return False

        if self._step == 1:
            await self.movement_service.gateway.transition(character)
            self._step = 2
            return False

        if self._step == 2:
            if character.position.x != self.x or character.position.y != self.y:
                await self.movement_service.move(character, self.x, self.y)
            return True
