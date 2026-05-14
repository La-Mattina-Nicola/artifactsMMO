from services import MovementService, GatherService, CraftingService


class TaskService:
    def __init__(
        self,
        movement: MovementService,
        gathering: GatherService,
        crafting: CraftingService,
    ):
        self.movement = movement
        self.gathering = gathering
        self.crafting = crafting

    async def execute_step(self, character, task):
        return await task.execute_step(character)
