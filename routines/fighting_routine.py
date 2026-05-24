from collections import deque

from data.world import World
from models.character import Character
from routines.routine import Routine
from services import EquipmentService, LoadoutPlanner
from services.banking import BankService
from tasks.deposit_task import DepositTask
from tasks.equip_task import EquipTask
from tasks.fight_task import FighterTask
from tasks.move_task import MoveToTask
from tasks.withdraw_task import WithdrawItemsTask


class FightingRoutine(Routine):
    def __init__(
        self,
        monster_code,
        world: "World",
        movement_service,
        fighting_service,
        bank_service: BankService,
        equipment_service: EquipmentService,
        loadout_planner: LoadoutPlanner,
        food_min: int = 2,
    ):
        self.monster_code = monster_code
        self.world = world
        self.movement_service = movement_service
        self.fighting_service = fighting_service
        self.bank_service = bank_service
        self.equipment_service = equipment_service
        self.loadout_planner = loadout_planner
        self.food_min = food_min
        self.pre_deposit_handled = True
        self._prepared = False
        self._phase = None
        self._prep_plan = deque()

    def generate_task(self, character: "Character"):
        if self._prep_plan:
            return self._prep_plan.popleft()

        if self._phase == "prepare":
            self._prepared = True
            self._phase = None
        elif self._phase == "restock":
            self._phase = None

        if not self._prepared:
            prep = self.loadout_planner.plan_fight(
                character,
                self.monster_code,
                food_min=0,
                food_target=0,
            )
            if prep.has_actions():
                self._prep_plan.append(DepositTask(self.bank_service))
                if prep.withdraw_items:
                    items = [
                        {"code": code, "quantity": qty}
                        for code, qty in prep.withdraw_items.items()
                        if qty > 0
                    ]
                    if items:
                        self._prep_plan.append(
                            WithdrawItemsTask(self.bank_service, items)
                        )
                for slot, code in prep.equip_changes.items():
                    self._prep_plan.append(
                        EquipTask(self.equipment_service, code, slot)
                    )
                self._prep_plan.append(DepositTask(self.bank_service))
                self._phase = "prepare"
                if self._prep_plan:
                    return self._prep_plan.popleft()

        if self._food_inventory_count(character) == 0:
            food_code = self._best_food_code()
            if food_code:
                target = max(1, int(character.inventory.max_items * 0.8))
                qty = min(target, self.bank_service.items.get(food_code, 0))
                if qty > 0:
                    self._prep_plan.append(DepositTask(self.bank_service))
                    self._prep_plan.append(
                        WithdrawItemsTask(
                            self.bank_service,
                            [{"code": food_code, "quantity": qty}],
                        )
                    )
                    self._phase = "restock"
                    return self._prep_plan.popleft()

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

    def _food_inventory_count(self, character: Character) -> int:
        total = 0
        for item in character.inventory.items:
            world_item = self.world.items.get(item.code)
            if world_item and world_item.is_food():
                total += item.quantity
        return total

    def _best_food_code(self) -> str | None:
        best_code = None
        best_heal = 0
        for code, item in self.world.items.items():
            if not item.is_food():
                continue
            if self.bank_service.items.get(code, 0) <= 0:
                continue
            heal = item.heal_value()
            if heal > best_heal:
                best_heal = heal
                best_code = code
        return best_code
