from core.simulation.metrics import compute_path_cost


def test_compute_path_cost(mock_graph):

    path = ["A", "B", "C"]

    cost = compute_path_cost(mock_graph, path)

    assert cost == 3