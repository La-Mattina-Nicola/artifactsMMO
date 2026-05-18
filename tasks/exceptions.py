class InventoryFullError(Exception):
    pass


class InventoryNotEmptyError(Exception):
    pass


class HealthPointTooLowError(Exception):
    pass


class InsufficientSkillLevelError(Exception):
    def __init__(self, skill: str, required_level: int, item_code: str, quantity: int):
        self.skill = skill
        self.required_level = required_level
        self.item_code = item_code
        self.quantity = quantity
