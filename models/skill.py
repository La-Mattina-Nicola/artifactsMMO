from dataclasses import dataclass
from models.skill_level import SkillLevel


@dataclass
class Skills:
    mining: SkillLevel
    woodcutting: SkillLevel
    fishing: SkillLevel
    weaponcrafting: SkillLevel
    gearcrafting: SkillLevel
    jewelrycrafting: SkillLevel
    cooking: SkillLevel
    alchemy: SkillLevel
