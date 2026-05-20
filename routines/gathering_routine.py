import logging
from data.world import World
from routines import Routine
from tasks.exceptions import InsufficientSkillLevelError
from tasks.gather_task import GatherTask
from tasks.move_task import MoveToTask


logger = logging.getLogger(__name__)


class GatheringRoutine(Routine):
    def __init__(self, drop_code, world: "World", movement_service, gathering_service):
        self.drop_code = drop_code
        self.world = world
        self.movement_service = movement_service
        self.gathering_service = gathering_service

    def generate_task(self, character):
        node = self.world.closest_node(
            self.drop_code, character.position.x, character.position.y
        )
        resource = self.world.resources.get(node.content_code)
        if resource:
            char_level = getattr(character.skills, resource.skill).level
            if char_level < resource.level:
                raise InsufficientSkillLevelError(resource.skill, resource.level)
        if node is None:
            raise ValueError(f"Aucun node trouvé pour le drop '{self.drop_code}'")
        if character.position.x != node.x or character.position.y != node.y or character.position.layer != node.layer:
            return MoveToTask(node.x, node.y, self.movement_service, layer=node.layer)

        return GatherTask(node, self.gathering_service)
