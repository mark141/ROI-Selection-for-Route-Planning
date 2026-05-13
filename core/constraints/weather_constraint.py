from core.base.constraint import Constraint


class WeatherConstraint(Constraint):

    def __init__(self, weather_data):
        self.weather_data = weather_data

    def evaluate(self, edge):

        data = self.weather_data.get(edge.id)

        if data is None:
            return True

        visibility_ok = data["visibility"] > 0.5
        wind_ok = data["wind_speed"] < 50

        return visibility_ok and wind_ok