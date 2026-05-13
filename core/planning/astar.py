import networkx as nx

from core.base.planner import Planner


class AStarPlanner(Planner):

    def compute_route(self, graph, start, goal):

        return nx.astar_path(
            graph,
            start,
            goal,
            weight="weight"
        )