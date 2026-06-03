from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class Constraint(ABC):
    """
    Base interface for all constraints.
    """

    @abstractmethod
    def evaluate(
        self,
        point: Tuple[float, float],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Returns:
        {
            "valid": bool,
            "cost": float,
            "meta": dict
        }
        """
        pass