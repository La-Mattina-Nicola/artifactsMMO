import logging
from collections import deque

from data.world import World
from routines import Routine
from services import EquipmentService, LoadoutPlanner
from services.banking import BankService
from tasks.deposit_task import DepositTask
from tasks.equip_task import EquipTask
from tasks.exceptions import InsufficientSkillLevelError
from tasks.gather_task import GatherTask
from tasks.move_task import MoveToTask
from tasks.withdraw_task import WithdrawItemsTask


logger = logging.getLogger(__name__)


class GatheringRoutine(Routine):
    def __init__(
        self,
        drop_code,
        world: "World",
        movement_service,
        gathering_service,
        bank_service: BankService,
        equipment_service: EquipmentService,
        loadout_planner: LoadoutPlanner,
    ):
        self.drop_code = drop_code
        self.world = world
        self.movement_service = movement_service
        self.gathering_service = gathering_service
        self.bank_service = bank_service
        self.equipment_service = equipment_service
        self.loadout_planner = loadout_planner
        self.pre_deposit_handled = True
        self._prepared = False
        self._phase = None
        self._prep_plan = deque()

    def generate_task(self, character):
        if self._prep_plan:
            return self._prep_plan.popleft()

        if self._phase == "prepare":
            self._prepared = True
            self._phase = None

        if not self._prepared:
            prep = self.loadout_planner.plan_gather(character, self.drop_code)
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

        node = self.world.closest_node(
            self.drop_code, character.position.x, character.position.y
        )
        if node is None:
            raise ValueError(f"Aucun node trouvé pour le drop '{self.drop_code}'")
        resource = self.world.resources.get(node.content_code)
        if resource:
            char_level = getattr(character.skills, resource.skill).level
            if char_level < resource.level:
                raise InsufficientSkillLevelError(resource.skill, resource.level)
        if (
            character.position.x != node.x
            or character.position.y != node.y
            or character.position.layer != node.layer
        ):
            return MoveToTask(node.x, node.y, self.movement_service, layer=node.layer)

        return GatherTask(node, self.gathering_service)
