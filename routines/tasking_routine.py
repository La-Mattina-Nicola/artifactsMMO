import logging
from collections import deque

from tasks import Task
from models.character import Character
from routines import Routine, FightingRoutine, GatheringRoutine
from tasks.craft_task import CraftTask
from tasks.deposit_task import DepositTask
from tasks.monster_goal_task import MonsterGoalTask
from tasks.move_task import MoveToTask
from tasks.goal_task import GoalTask
from tasks import TradeTask, AcceptTask, CompleteTask, WithdrawTask
from services import (
    MovementService,
    TaskService,
    GatherService,
    FightingService,
    CraftingService,
    BankService,
)
from data.world import World

logger = logging.getLogger(__name__)

TASK_MASTERS = {
    "items": (4, 13),
    "monsters": (1, 2),
}


class TaskingRoutine(Routine):
    def __init__(
        self,
        movement_service: MovementService,
        tasking_service: TaskService,
        gathering_service: GatherService,
        fighting_service: FightingService,
        bank_service: BankService,
        craft_service: CraftingService,
        world: World,
        task_type: str = "items",
        fallback_drop: str | None = None,
    ):
        self.movement_service = movement_service
        self.tasking_service = tasking_service
        self.gathering_service = gathering_service
        self.fighting_service = fighting_service
        self.bank_service = bank_service
        self.craft_service = craft_service
        self.world = world
        self.task_type = task_type
        self.fallback_drop = fallback_drop

        self.plan = deque()

    # -----------------------------
    # MAIN ENTRY POINT
    # -----------------------------
    def generate_task(self, character):
        logger.debug("%s — generate_task", character.name)

        # 1. Si plan en cours → exécuter
        if self.plan:
            return self.plan.popleft()

        task = character.task

        # -----------------------------
        # 2. Pas de quête → accept
        # -----------------------------
        if character.task is None or not character.task.name:
            if self.task_type is None:
                self.task_type = "items"
            tx, ty = TASK_MASTERS[self.task_type]
            if (character.position.x, character.position.y) != (tx, ty):
                return MoveToTask(tx, ty, self.movement_service)

            return AcceptTask(self.tasking_service)

        # -----------------------------
        # 3. Quête terminée → complete
        # -----------------------------
        if task.progress >= task.total:
            self.plan.clear()
            tx, ty = TASK_MASTERS.get(task.type, TASK_MASTERS["items"])
            if (character.position.x, character.position.y) != (tx, ty):
                return MoveToTask(tx, ty, self.movement_service)

            return CompleteTask(self.tasking_service)

        # -----------------------------
        # 4. Build plan si items
        # -----------------------------
        if task.type == "items":
            self.plan = self._build_item_plan(character, task)
            if self.plan:
                return self.plan.popleft()

        # -----------------------------
        # 5. fallback monster
        # -----------------------------
        if task.type == "monsters":
            routine = FightingRoutine(
                monster_code=task.name,
                world=self.world,
                movement_service=self.movement_service,
                fighting_service=self.fighting_service,
            )
            return MonsterGoalTask(
                target_progress=task.total,
                routine=routine,
            )

        raise ValueError(f"Unknown task type: {task.type}")

    # -----------------------------
    # PLAN BUILDER
    # -----------------------------
    def _build_item_plan(self, character: Character, task: Task):
        plan = deque()

        needed = task.total - task.progress
        inv_qty = character.inventory.count(task.name)
        bank_qty = self.bank_service.items.get(task.name, 0)

        remaining = needed - inv_qty

        logger.debug(
            "PLAN BUILD %s needed=%d inv=%d bank=%d remaining=%d",
            task.name,
            needed,
            inv_qty,
            bank_qty,
            remaining,
        )

        # -----------------------------
        # 1. UTILISER INVENTAIRE DIRECT
        # -----------------------------
        if inv_qty > 0:
            tx, ty = TASK_MASTERS["items"]

            if (character.position.x, character.position.y) != (tx, ty):
                plan.append(MoveToTask(tx, ty, self.movement_service))

            give = min(inv_qty, needed)

            plan.append(
                TradeTask(
                    tasking_service=self.tasking_service,
                    item_code=task.name,
                    quantity=give,
                )
            )

            return plan

        # -----------------------------
        # 2. RÉCUP BANQUE SI POSSIBLE
        # -----------------------------
        if bank_qty > 0:
            bx, by = self.bank_service.closest_bank(
                character.position.x,
                character.position.y,
            )
            needed = character.task.total - character.task.progress
            batch = min(character.inventory.max_items, needed, bank_qty)

            plan.append(MoveToTask(bx, by, self.movement_service))
            plan.append(DepositTask(self.bank_service))

            plan.append(
                WithdrawTask(
                    self.bank_service,
                    task.name,
                    batch,
                )
            )

            # après withdraw → retour PNJ
            tx, ty = TASK_MASTERS["items"]
            plan.append(MoveToTask(tx, ty, self.movement_service))

            plan.append(
                TradeTask(
                    tasking_service=self.tasking_service,
                    item_code=task.name,
                    quantity=batch,
                )
            )

            return plan

        # -----------------------------
        # 3. CRAFT SI RIEN EN BANQUE
        # -----------------------------
        item = self.world.items.get(task.name)

        if item and item.craft:
            has_resources = all(
                self.bank_service.items.get(ing.code, 0) >= ing.quantity
                for ing in item.craft.items
            )
            if not has_resources:
                # farmer les ingrédients manquants...
                for ing in item.craft.items:
                    available = self.bank_service.items.get(ing.code, 0)
                    if available < ing.quantity:
                        missing = ing.quantity - available
                        routine = GatheringRoutine(
                            drop_code=ing.code,
                            world=self.world,
                            movement_service=self.movement_service,
                            gathering_service=self.gathering_service,
                        )
                        plan.append(
                            GoalTask(
                                item_code=ing.code,
                                target_quantity=missing,
                                routine=routine,
                            )
                        )
                return plan

            # ✅ Si ressources OK → ajouter le CraftTask
            plan.append(
                CraftTask(
                    item=item,
                    quantity=needed,
                    bank_service=self.bank_service,
                    craft_service=self.craft_service,
                    movement_service=self.movement_service,
                )
            )
            return plan  # ← manquait

        # -----------------------------
        # 4. FARM fallback
        # -----------------------------
        routine = GatheringRoutine(
            drop_code=task.name,
            world=self.world,
            movement_service=self.movement_service,
            gathering_service=self.gathering_service,
        )

        plan.append(
            GoalTask(
                item_code=task.name,
                target_quantity=remaining,
                routine=routine,
            )
        )

        return plan
