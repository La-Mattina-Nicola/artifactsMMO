from models import Character
from tasks.base_task import Task
from services.equipment import EquipmentService
from tasks.exceptions import HealthPointTooLowError


class EquipTask(Task):
    def __init__(self, equipment_service: EquipmentService, item_code: str, slot: str):
        self.equipment_service = equipment_service
        self.item_code = item_code
        self.slot = slot

    async def execute_step(self, character: Character) -> bool:
        if self.equipment_service.is_equipped(character, self.item_code):
            return True
        if self.equipment_service.is_equipped(
            character, self.item_code, slot=self.slot
        ):
            return True
        if character.stats.hp < character.stats.max_hp:
            raise HealthPointTooLowError()
        await self.equipment_service.equip(character, self.item_code, slot=self.slot)
        return True
