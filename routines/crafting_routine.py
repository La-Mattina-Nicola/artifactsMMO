import logging
from routines.routine import Routine
from tasks.craft_task import CraftTask

logger = logging.getLogger(__name__)


class CraftingRoutine(Routine):
    def __init__(
        self, item_code: str, bank_service, craft_service, movement_service, world
    ):
        self.item_code = item_code
        self.bank_service = bank_service
        self.craft_service = craft_service
        self.movement_service = movement_service
        self.world = world

    def generate_task(self, character):
        item = self.world.items.get(self.item_code)
        if item is None or item.craft is None:
            raise ValueError(f"Item inconnu ou non craftable : {self.item_code}")

        # Vérifier qu'on peut faire au moins 1 craft
        has_resources = all(
            self.bank_service.items.get(ing.code, 0) >= ing.quantity
            for ing in item.craft.items
        )

        if not has_resources:
            logger.info(
                "CraftingRoutine — plus de ressources pour crafter %s", item.name
            )
            raise StopIteration(f"Plus de ressources pour {item.name}")

        # Calculer le batch max
        max_by_inventory = character.inventory.max_items // sum(
            i.quantity for i in item.craft.items
        )
        max_by_bank = min(
            self.bank_service.items.get(ing.code, 0) // ing.quantity
            for ing in item.craft.items
        )
        batch = max(1, min(max_by_inventory, max_by_bank))

        return CraftTask(
            item=item,
            quantity=batch,
            bank_service=self.bank_service,
            craft_service=self.craft_service,
            movement_service=self.movement_service,
        )
