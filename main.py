from core.constraints.weather_constraint import WeatherConstraint
from core.roi.static_roi import ROISelectorFactory
from core.base.scenario import Scenario
from core.roi.dynamic_roi import DynamicROISelector
from core.planning.route_manager import RouteManager
from utils.graph_utils import OSRMRoutingAPI


def main():

    start = (47.5596, 7.5886)  # Basel
    goal = (46.5197, 6.6323)  # Lausanne

    # start = (45.0703, 7.6869)  # Turin
    # goal = (44.4949, 11.3426)  # Bologna

    constraints = {
        "max_rain": 1.5,
        # has to be in range 3 month before TODAY
        "start_date": "2026-06-01",
        # has to be in range 15 days after TODAY
        "end_date": "2026-06-02",
        "buffer": 0.05    # Buffer % dependant on route length
    }

    # set dataclass inputs
    scenario = Scenario(
        start=start,
        goal=goal,
        constraints=constraints
    )

    # Static ROI -> first ROI
    # BBox: Bounding Box (BASELINE)
    # ABBox: Aligned Bounding Box
    # CHull: Convex Hull
    # BCorr: Buffered Corridor
    # GRIDExpand: Grid Expansion model

    # get initial shape of ROI
    # TODO: CHull BCorr ...
    init_roi = ROISelectorFactory.create(scenario, "BBox")

    # Set weather API data
    weather_constraint = WeatherConstraint()
    weather_constraint.fetch_weather(
        grid_df=init_roi.roi_df,
        start_date=scenario.constraints["start_date"],
        end_date=scenario.constraints["end_date"]
    )

    # ROI generation/iteration
    roi_selector = DynamicROISelector(
        constraints=[weather_constraint]
    )
    # TODO: make generation/iteration
    result = roi_selector.generate(scenario)

    # TODO: save all iteration steps in the class
    print("ROI RESULT")
    print(result["roi"])

    route_manager = RouteManager(
        # TODO: needs update! -> use ORSRoutingAPI
        routing_api=OSRMRoutingAPI()
    )

    # TODO: needs update!
    route = route_manager.calculate_route(
        start,
        goal,
        result["roi"]
    )

    # TODO: utils.visualization -> different scenarios to add as a group:
    #  start+end                        ->haversine-graph
    #  start+end+init_roi               ->haversine-graph + init_roi
    #  route                            ->replaces start+end (so no more haversine-graph)
    #  route+init_roi+result_roi        ->comparison of roi and the route in the result roi
    #  init_roi+result_roi+rain_points  ->visualization of rain avoidance
    print("ROUTE")
    print(route)

if __name__ == "__main__":
    main()