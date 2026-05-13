from core.constraints.weather_constraint import WeatherConstraint


def test_weather_constraint_pass(mock_weather, mock_edge):

    constraint = WeatherConstraint(mock_weather)

    result = constraint.evaluate(mock_edge)

    assert result is True


def test_weather_constraint_fail(mock_weather):

    class Edge:
        def __init__(self, edge_id):
            self.id = edge_id

    edge = Edge(("B", "C"))

    constraint = WeatherConstraint(mock_weather)

    result = constraint.evaluate(edge)

    assert result is False