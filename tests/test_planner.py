from core.planning.astar import AStarPlanner


def test_astar_finds_path(mock_graph):

    planner = AStarPlanner()

    path = planner.compute_route(
        graph=mock_graph,
        start="A",
        goal="C"
    )

    assert path[0] == "A"
    assert path[-1] == "C"