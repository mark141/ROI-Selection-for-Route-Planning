class RouteManager:

    def __init__(self, routing_api):
        self.routing_api = routing_api

    def calculate_route(
        self,
        start,
        goal,
        roi
    ):

        return self.routing_api.route(
            start=start,
            goal=goal,
            roi=roi
        )