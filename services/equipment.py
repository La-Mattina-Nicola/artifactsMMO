from api import ArtifactsGateway
from models import Character


class EquipmentService:
    def __init__(self, gateway: ArtifactsGateway):
        self.gateway = gateway

    def equipped_code(self, character: Character, slot: str) -> str | None:
        value = getattr(character.equipment, slot, None)
        if isinstance(value, tuple):
            return value[0]
        return value

    def all_equipped_codes(self, character: Character) -> list[str]:
        codes = []
        for slot in (
            "weapon",
            "rune",
            "shield",
            "helmet",
            "body_armor",
            "leg_armor",
            "boots",
            "ring1",
            "ring2",
            "amulet",
            "artifact1",
            "artifact2",
            "artifact3",
            "utility1",
            "utility2",
            "bag",
        ):
            code = self.equipped_code(character, slot)
            if code:
                codes.append(code)
        return codes

    def is_equipped(
        self, character: Character, item_code: str, slot: str | None = None
    ) -> bool:
        if slot:
            return self.equipped_code(character, slot) == item_code
        return item_code in self.all_equipped_codes(character)

    async def equip(
        self,
        character: Character,
        item_code: str,
        slot: str | None = None,
        quantity: int = 1,
    ):
        await self.gateway.equip_item(
            character, item_code, slot=slot, quantity=quantity
        )

    async def unequip(self, character: Character, slot: str, quantity: int = 1):
        await self.gateway.unequip_item(character, slot, quantity=quantity)
