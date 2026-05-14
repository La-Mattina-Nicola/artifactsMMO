from dataclasses import dataclass
from datetime import datetime, timezone
from models.stat import Stats
from models.skill import Skills
from models.skill_level import SkillLevel
from models.position import Position
from models.cooldown import Cooldowns
from models.equipment import Equipment
from models.inventory import Inventory
from models.inventory_item import InventoryItem
from models.character_task import CharacterTask


@dataclass
class Character:
    name: str
    account: str
    skin: str
    level: int
    xp: int
    max_xp: int
    gold: int
    speed: int
    stats: Stats
    skills: Skills
    position: Position
    cooldowns: Cooldowns
    equipment: Equipment
    inventory: Inventory
    task: CharacterTask

    @classmethod
    def from_dto(cls, data: dict) -> "Character":
        d = data["data"]
        return cls(
            name=d["name"],
            account=d["account"],
            skin=d["skin"],
            level=d["level"],
            xp=d["xp"],
            max_xp=d["max_xp"],
            gold=d["gold"],
            speed=d["speed"],
            stats=Stats(
                hp=d["hp"],
                max_hp=d["max_hp"],
                haste=d["haste"],
                critical_strike=d["critical_strike"],
                wisdom=d["wisdom"],
                prospecting=d["prospecting"],
                initiative=d["initiative"],
                threat=d["threat"],
                attack_fire=d["attack_fire"],
                attack_earth=d["attack_earth"],
                attack_water=d["attack_water"],
                attack_air=d["attack_air"],
                dmg=d["dmg"],
                dmg_fire=d["dmg_fire"],
                dmg_earth=d["dmg_earth"],
                dmg_water=d["dmg_water"],
                dmg_air=d["dmg_air"],
                res_fire=d["res_fire"],
                res_earth=d["res_earth"],
                res_water=d["res_water"],
                res_air=d["res_air"],
            ),
            skills=Skills(
                mining=SkillLevel(
                    d["mining_level"], d["mining_xp"], d["mining_max_xp"]
                ),
                woodcutting=SkillLevel(
                    d["woodcutting_level"], d["woodcutting_xp"], d["woodcutting_max_xp"]
                ),
                fishing=SkillLevel(
                    d["fishing_level"], d["fishing_xp"], d["fishing_max_xp"]
                ),
                weaponcrafting=SkillLevel(
                    d["weaponcrafting_level"],
                    d["weaponcrafting_xp"],
                    d["weaponcrafting_max_xp"],
                ),
                gearcrafting=SkillLevel(
                    d["gearcrafting_level"],
                    d["gearcrafting_xp"],
                    d["gearcrafting_max_xp"],
                ),
                jewelrycrafting=SkillLevel(
                    d["jewelrycrafting_level"],
                    d["jewelrycrafting_xp"],
                    d["jewelrycrafting_max_xp"],
                ),
                cooking=SkillLevel(
                    d["cooking_level"], d["cooking_xp"], d["cooking_max_xp"]
                ),
                alchemy=SkillLevel(
                    d["alchemy_level"], d["alchemy_xp"], d["alchemy_max_xp"]
                ),
            ),
            position=Position(
                x=d["x"],
                y=d["y"],
                layer=d["layer"],
                map_id=d["map_id"],
            ),
            cooldowns=Cooldowns(
                value=d["cooldown"],
                expiration=datetime.fromisoformat(d["cooldown_expiration"]),
            ),
            equipment=Equipment(
                weapon=d["weapon_slot"],
                rune=d["rune_slot"],
                shield=d["shield_slot"],
                helmet=d["helmet_slot"],
                body_armor=d["body_armor_slot"],
                leg_armor=d["leg_armor_slot"],
                boots=d["boots_slot"],
                ring1=d["ring1_slot"],
                ring2=d["ring2_slot"],
                amulet=d["amulet_slot"],
                artifact1=d["artifact1_slot"],
                artifact2=d["artifact2_slot"],
                artifact3=d["artifact3_slot"],
                utility1=(d["utility1_slot"], d["utility1_slot_quantity"]),
                utility2=(d["utility2_slot"], d["utility2_slot_quantity"]),
                bag=d["bag_slot"],
            ),
            inventory=Inventory(
                max_items=d["inventory_max_items"],
                items=[
                    InventoryItem(
                        slot=i["slot"], code=i["code"], quantity=i["quantity"]
                    )
                    for i in (d.get("inventory") or [])
                    if i["code"]
                ],
            ),
            task=CharacterTask(
                name=d["task"],
                type=d["task_type"],
                progress=d["task_progress"],
                total=d["task_total"],
            ),
        )

    def update_from_dto(self, data: dict):
        updated = Character.from_dto(data)
        self.__dict__.update(updated.__dict__)

    @property
    def cooldown_remaining(self) -> int:
        if not self.cooldowns.expiration:
            return 0

        now = datetime.now(timezone.utc)
        remaining = (self.cooldowns.expiration - now).total_seconds()

        return max(0, int(remaining))
