from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from tasks import Task
from tasks.exceptions import InventoryNotEmptyError
from models.item import Item

if TYPE_CHECKING:
    from models.character import Character
    from services import CraftingService
    from services.movement import MovementService
    from services.banking import BankService


logger = logging.getLogger(__name__)


class CraftTask(Task):
    retry_on_fail = False

    def __init__(
        self,
        item: Item,
        quantity,
        bank_service: BankService,
        craft_service: CraftingService,
        movement_service: MovementService,
    ):
        super().__init__()
        self.item = item
        self.total_quantity = quantity
        self.crafted = 0
        self.bank_service = bank_service
        self.craft_service = craft_service
        self.movement_service = movement_service
        self._step = 0

    async def execute_step(self, character: Character) -> bool:
        logger.debug(f"CraftTask: {self._step}")
        if self._step == 0:
            if self.item.craft is None:
                logger.warning("L'item %s n'est pas craftable", self.item.name)
                return True
            has_resources = await self.bank_service.has_ingredients(
                self.item, self.total_quantity
            )
            if not has_resources:
                logger.warning(
                    "Pas assez de ressources en banque pour crafter %s", self.item
                )
                return True
            self._step = 1
            return False

        # Step 1 - deposer inventaire à la banque
        if self._step == 1:
            logger.debug("Inventory empty ? %s", character.inventory.is_empty())
            if not character.inventory.is_empty():
                raise InventoryNotEmptyError()
            self._step = 2
            return False

        # Step 2 — se déplacer à la banque
        if self._step == 2:
            bx, by = self.bank_service.closest_bank(
                character.position.x, character.position.y
            )
            logger.debug(
                "%s — step 2 : pos=(%d,%d) bank=(%d,%d)",
                character.name,
                character.position.x,
                character.position.y,
                bx,
                by,
            )
            if character.position.x != bx or character.position.y != by:
                await self.movement_service.move(character, bx, by)
                return False
            self._step = 3
            logger.debug("%s — step 2 → step 3", character.name)
            return False

        # Step 3 — retirer les items nécessaires de la banque
        if self._step == 3:
            logger.debug(
                "%s — step 3 : withdraw %s x%d",
                character.name,
                self.item.code,
                self.quantity,
            )
            remaining = self.total_quantity - self.crafted
            max_batch = self._max_batch_size(character)
            self.current_batch = min(remaining, max_batch)

            await self.bank_service.withdraw_ingredients(
                character, self.item, self.current_batch
            )
            self._step = 4
            return False

        # Step 4 — se déplacer à l'atelier
        if self._step == 4:
            wx, wy = await self.craft_service.get_workshop(self.item)
            logger.debug(
                "%s — step 4 : pos=(%d,%d) workshop=(%d,%d)",
                character.name,
                character.position.x,
                character.position.y,
                wx,
                wy,
            )
            if character.position.x != wx or character.position.y != wy:
                await self.movement_service.move(character, wx, wy)
                return False
            self._step = 5
            return False

        # Step 5 — crafter
        if self._step == 5:
            await self.craft_service.craft(character, self.item, self.current_batch)
            self.crafted += self.current_batch
            logger.info(
                f"{character.name} a crafté {self.current_batch}x {self.item.code}"
            )
            if self.crafted >= self.total_quantity:
                return True
            self._step = 1
            return False

    def _max_batch_size(self, character: Character) -> int:
        inventory_space = character.inventory.max_items
        ingredients_per_craft = sum(i.quantity for i in self.item.craft.items)
        return max(1, inventory_space // ingredients_per_craft)
