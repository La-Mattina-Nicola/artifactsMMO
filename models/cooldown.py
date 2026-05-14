from dataclasses import dataclass
import datetime


@dataclass
class Cooldowns:
    value: int
    expiration: datetime
