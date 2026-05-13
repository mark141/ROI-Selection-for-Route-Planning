from core.constraints.weather_constraint import WeatherConstraint
from core.roi.static_roi import StaticROISelector
from core.planning.astar import AStarPlanner

from core.simulation.metrics import compute_path_cost

import networkx as nx


def build_graph():
    """
    Creates a small example graph.
    """

    graph = nx.Graph()

    graph.add_edge("A", "B", weight=1)
    graph.add_edge("B", "C", weight=2)
    graph.add_edge("A", "C", weight=4)

    return graph


def load_weather_data():
    """
    Mock weather dataset.
    """

    return {
        ("A", "B"): {
            "visibility": 0.9,
            "wind_speed": 10
        },
        ("B", "C"): {
            "visibility": 0.2,
            "wind_speed": 80
        }
    }


def main():

    # Scenario setup
    graph = build_graph()

    start = "A"
    goal = "C"

    weather_data = load_weather_data()

    # Constraints
    weather_constraint = WeatherConstraint(weather_data)

    constraints = [weather_constraint]

    # ROI Selection
    roi_selector = StaticROISelector()

    roi = roi_selector.select_region(
        graph=graph,
        start=start,
        goal=goal,
        constraints=constraints
    )

    print("Selected ROI:")
    print(roi)

    # Route Planning
    planner = AStarPlanner()

    path = planner.compute_route(
        graph=graph,
        start=start,
        goal=goal
    )

    print("\nComputed Path:")
    print(path)

    # Evaluation

    cost = compute_path_cost(graph, path)

    print("\nPath Cost:")
    print(cost)


if __name__ == "__main__":
    main()