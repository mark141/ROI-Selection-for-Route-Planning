# this would be part of the full routing engine and is not part of the Thesis

from abc import ABC, abstractmethod


class Planner(ABC):

    @abstractmethod
    def compute_route(self, graph, start, goal):
        pass