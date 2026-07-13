# this would be part of the full routing engine and is not part of the Thesis
# this is only an example of an Astar routing from networkx library

import networkx as nx

from core.interfaces.planner import Planner


class AStarPlanner(Planner):

    def compute_route(self, graph, start, goal):

        return nx.astar_path(
            graph,
            start,
            goal,
            weight="weight"
        )