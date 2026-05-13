from abc import ABC, abstractmethod


class Constraint(ABC):

    @abstractmethod
    def evaluate(self, node_or_edge):
        """
        Returns whether the constraint is satisfied.
        """
        pass