from abc import ABC, abstractmethod


class Planner(ABC):

    @abstractmethod
    def compute_route(self, graph, start, goal):
        pass