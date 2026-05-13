from abc import ABC, abstractmethod


class ROISelector(ABC):

    @abstractmethod
    def select_region(self, graph, start, goal, constraints):
        """
        Returns a region of interest for routing.
        """
        pass