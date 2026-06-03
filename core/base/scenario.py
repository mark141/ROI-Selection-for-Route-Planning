from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class Scenario:
    start: Tuple[float, float]
    goal: Tuple[float, float]
    constraints: Dict