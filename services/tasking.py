from api.artifacts_gateway import ArtifactsGateway
from services import MovementService


class TaskService:
    def __init__(
        self,
        gateway: ArtifactsGateway,
        movement: MovementService,
    ):
        self.gateway = gateway
        self.movement = movement

    async def execute_step(self, character, task):
        return await task.execute_step(character)

    async def accept_task(self, character):
        await self.gateway.accept_quest(character)

    async def complete_task(self, character):
        await self.gateway.complete_quest(character)

    async def trade_task(self, character, item_code: str, quantity: int):
        await self.gateway.trade_quest(character, item_code, quantity)
