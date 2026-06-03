import requests
import openrouteservice
from utils.config import routing_api


class ORSRoutingAPI:

    def route(self, start, goal, roi=None):

        start_lon, start_lat = start[1], start[0]
        goal_lon, goal_lat = goal[1], goal[0]
        coords = (start_lon, start_lat, goal_lon, goal_lat)

        client = openrouteservice.Client(key=routing_api["key"])

        response = client.directions(
            coords,
            profile="driving-car",
            format="geojson",
            alternative_routes={
                "target_count": 2,  # request up to 3 alternatives
                "share_factor": 0.6,  # how much overlap is acceptable
                "weight_factor": 2 # allow alternatives up to 2x length of main
            },
            timeout=10
        )

        return response.json()


class OSRMRoutingAPI:

    BASE_URL = "http://router.project-osrm.org"

    def route(self, start, goal, roi=None):

        start_lon, start_lat = start[1], start[0]
        goal_lon, goal_lat = goal[1], goal[0]

        url = (
            f"{self.BASE_URL}/route/v1/driving/"
            f"{start_lon},{start_lat};{goal_lon},{goal_lat}"
            f"?overview=full&geometries=geojson"
        )

        response = requests.get(url, timeout=10)

        return response.json()