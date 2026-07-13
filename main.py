# This is an example usage of the build library

import pandas as pd

from core.constraints.weather_constraint import WeatherConstraint
from core.roi.roi import ROISelectorFactory
from core.base.scenario import Scenario
from core.roi.roi_iterator import ROIIterator
from utils.geometry import reachable, to_simple_polygon
from utils.visualization import plotter


def main():

    start = (52.5200, 13.4050)  # Berlin
    goal = (48.8566, 2.3522)  # Paris

    # 2026-07-08 05:00
    departure_time = pd.Timestamp("2026-07-6 8:06")

    # https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?lv2=101812&lv3=101906&utm_source=chatgpt.com
    # precipitation thresholds:
    # 0 < x < 2,5 mm light rain
    # 2,5 <= x < 10 mm medium rain
    # 10 <= x < 50 mm heavy rain
    # 50 <= x mm very heavy rain (flooding expected)
    constraints = {
        # maximum precipitation in mm
        "max_rain": 1.5,
        # has to be in range 3 month before TODAY
        "start_date": "2026-07-06",
        # has to be in range 15 days after TODAY
        "end_date": "2026-07-08",
        "buffer": 0.05,    # Buffer % dependant on route length
        # departure // timeframe
        "mode": "departure",
        # will get rounded to "full hours"
        "departure_time": departure_time,
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
    # TODO: Ellipsoid

    # get initial shape of ROI
    init_roi = ROISelectorFactory.create(scenario, "BBox")

    # Set weather API data
    weather_constraint = WeatherConstraint()
    weather_constraint.fetch_weather(
        grid_df=init_roi.roi_df,
        start_date=scenario.constraints["start_date"],
        end_date=scenario.constraints["end_date"]
    )
    print(
        len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] <= 0.6])
    )
    print(
        len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] > 0.6])
    )
    print(weather_constraint.weather_df["precipitation"].max())

    # ROI generation/iteration
    # what it does?
    # class - takes start_roi & weather_constraints & scenario as input
    # also need to declare if start-now or timeframe calcs should be done
    # has functions:
    # - iterate - always does 1 iteration step, whereas the first iteration step is the initial generation
    # - run_iterations - runs multiple iteration steps or until failure
    # - helper functions that are getting called in the iterate function
    roi_iterator = ROIIterator(
        initial_roi=init_roi,
        constraints={"weather_constraint": weather_constraint},
        scenario=scenario,
        mode=scenario.constraints["mode"],
    )
    # default 5 runs - each run -0.1 precipitation
    # all steps are saved in the class roi_iterator
    roi = roi_iterator.run_iterations(n=10)
    # TODO: use mechanic like to_simple_polygon to get roi in a single polygon
    if roi.interiors != 0:
        roi2 = to_simple_polygon(roi)
    # print("ROI RESULT")
    # print(roi)
    # TODO: display ROI and basemap and start + end
    #   optional: haversine graph
    #   optional: initial_roi
    #   optional: route
    # plot test
    reachable_df = reachable(
        df=weather_constraint.weather_df.copy(),
        start=scenario.start,
        departure_time=departure_time,
        avg_speed=80,
    )
    print(len(reachable_df[reachable_df["precipitation"] <= roi_iterator.threshhold]))
    print(len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshhold]))
    plotter(
        reachable_df,
        init_roi.roi_df,
        roi,
        start,
        goal,
        roi_iterator.threshhold
    )
    # plot the simple polygon which can be given to the API
    plotter(
        reachable_df,
        init_roi.roi_df,
        roi2,
        start,
        goal,
        roi_iterator.threshhold
    )

    # TODO: add routing and plot it as well

# if __name__ == "__main__":
#     main()