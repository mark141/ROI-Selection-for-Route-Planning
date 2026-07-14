"""
All Scenarios are tested with:

-ROI reduction Ratio:
ROI_reduction = 1 - ( Area(final ROI))/(Area(inital ROI))

-Rain avoidance Ratio:
Rain_reduction = 1 - (RainPoints(final)) / (RainPoints((inital))

-Connectivity success rate
is given due to implementation
-> how many iteration until stop?

- Runtime
measure:
Component		    Time
ROI creation		ms
weather API request	seconds
polygon generation	ms
full iteration		seconds


For all Tests:
Start is always Berlin. Destination is always Paris.
The buffer for the iteration stays at 0.05. Resulting in a percentage buffer of the distance of 5%.

The variables:
-departure time
-the rain tolerance of precipitation in mm
-timeframe for the weather data
-mode: departure/timeframe

The scenarios:
-Localized rain -> expected: holes appear and ROI shrinks
-no rain  scenario -> expected: roi stays almost unchanged
-Heavy rain corridor -> expected: threshold reduces and eventually stops
-No feasible connection -> expected: previous valid ROI returned
-different departure -> expected: the used departure time has the least precipitation
"""


import pandas as pd
import geopandas as gpd

from core.constraints.weather_constraint import WeatherConstraint
from core.roi.roi import ROISelectorFactory
from core.interfaces.scenario import Scenario
from core.roi.roi_iterator import ROIIterator
from core.simulation.evaluator import EvaluationResult, Timer
from core.simulation.metrics import roi_metrics, constraint_metrics
from utils.geometry import reachable, to_simple_polygon, create_rain_barrier
from utils.dates import evaluate_departure_times
from utils.visualization import plot_roi_result


def scenario_localized_rain():
    """
    Localized rain -> expected: holes appear and ROI shrinks
    """
    start = (52.5200, 13.4050)  # Berlin
    goal = (48.8566, 2.3522)  # Paris

    # has to be in the start_date and ebd_date timeframes
    departure_time = pd.Timestamp("2026-07-6 8:06")

    # https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?lv2=101812&lv3=101906&utm_source=chatgpt.com
    # precipitation thresholds:
    # 0 < x < 2,5 mm light rain
    # 2,5 <= x < 10 mm medium rain
    # 10 <= x < 50 mm heavy rain
    # 50 <= x mm very heavy rain (flooding expected)
    constraints = {
        # maximum precipitation in mm
        "max_rain": 3,
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
    # BBox: Bounding Box
    # ABBox: Aligned Bounding Box
    # possible additons: Ellipsoid

    timer = Timer()

    # get initial shape of ROI
    init_roi = ROISelectorFactory.create(scenario, "BBox")

    roi_creation_time = timer.stop()

    # Set weather API data
    timer = Timer()
    weather_constraint = WeatherConstraint()
    weather_constraint.fetch_weather(
        grid_df=init_roi.roi_df,
        start_date=scenario.constraints["start_date"],
        end_date=scenario.constraints["end_date"]
    )
    weather_request_time = timer.stop()
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] <= 0.6])
    # )
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] > 0.6])
    # )
    # print(weather_constraint.weather_df["precipitation"].max())

    # ROI generation/iteration
    # what it does?
    # class - takes start_roi & weather_constraints & scenario as input
    # either start-now or timeframe based calculation
    # has functions:
    # - iterate - always does 1 iteration step, whereas the first iteration step is the initial generation
    # - run_iterations - runs multiple iteration steps or until failure
    # - helper functions that are getting called in the iterate function
    # - stores every iteration step inside the class as metadata
    roi_iterator = ROIIterator(
        initial_roi=init_roi,
        constraints={"weather_constraint": weather_constraint},
        scenario=scenario,
        mode=scenario.constraints["mode"],
    )
    # default 5 runs - each run -0.1 precipitation
    # all steps are saved in the class roi_iterator
    timer = Timer()
    roi = roi_iterator.run_iterations(n=30)
    iteration_time = timer.stop()

    # use mechanic like to_simple_polygon to get roi in a single polygon without interiors
    if roi.interiors != 0:
        roi2 = to_simple_polygon(roi)
    # plot test
    reachable_df = reachable(
        df=weather_constraint.weather_df.copy(),
        start=scenario.start,
        departure_time=departure_time,
        avg_speed=80,
    )
    # print(len(reachable_df[reachable_df["precipitation"] <= roi_iterator.threshold]))
    # print(len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold]))

    roi_gdf = gpd.GeoDataFrame(
        geometry=[roi],
        crs="EPSG:4326"
    )
    # metrics
    (
        initial_area,
        final_area,
        roi_reduction,
        remaining_area,
    ) = roi_metrics(init_roi.roi_df.to_crs("EPSG:3035"), roi_gdf.to_crs("EPSG:3035"))

    (
        reachable_points,
        satisfying_points,
        violating_points,
        constraint_satisfaction,
    ) = constraint_metrics(
        reachable_df,
        0,
    )

    result = EvaluationResult(
        scenario="Localized Rain",

        # -----------------------------
        # Runtime
        # -----------------------------
        roi_creation_time=roi_creation_time,
        weather_request_time=weather_request_time,
        iteration_time=iteration_time,
        total_runtime=(
                roi_creation_time
                + weather_request_time
                + iteration_time
        ),

        # -----------------------------
        # ROI
        # -----------------------------
        initial_area=initial_area[0],
        final_area=final_area[0],
        roi_reduction=roi_reduction[0],
        remaining_area=remaining_area[0],

        # -----------------------------
        # Constraint Satisfaction
        # -----------------------------
        reachable_points=reachable_points,
        satisfying_points=int(satisfying_points),
        violating_points=int(violating_points),
        constraint_satisfaction=float(constraint_satisfaction),

        # -----------------------------
        # Iteration
        # -----------------------------
        iterations=roi_iterator.iteration,
        final_threshold=roi_iterator.threshold,
        holes=len(roi.interiors),
        connected=True,

        departure_time=str(departure_time),
    )

    result.print_summary()

    # plot_roi_result(
    #     reachable_df,
    #     init_roi.roi_df,
    #     roi,
    #     start,
    #     goal,
    #     roi_iterator.threshold
    # )
    # # plot the simple polygon which can be given to the API
    # if roi.interiors != 0:
    #     plot_roi_result(
    #         reachable_df,
    #         init_roi.roi_df,
    #         roi2,
    #         start,
    #         goal,
    #         roi_iterator.threshold
    #     )


def scenario_no_rain():
    """
    no rain  scenario -> expected: roi stays almost unchanged
    """
    start = (52.5200, 13.4050)  # Berlin
    goal = (48.8566, 2.3522)  # Paris

    # has to be in the start_date and ebd_date timeframes
    departure_time = pd.Timestamp("2026-06-26 7:00")

    # https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?lv2=101812&lv3=101906&utm_source=chatgpt.com
    # precipitation thresholds:
    # 0 < x < 2,5 mm light rain
    # 2,5 <= x < 10 mm medium rain
    # 10 <= x < 50 mm heavy rain
    # 50 <= x mm very heavy rain (flooding expected)
    constraints = {
        # maximum precipitation in mm
        "max_rain": 3,
        # has to be in range 3 month before TODAY
        "start_date": "2026-06-25",
        # has to be in range 15 days after TODAY
        "end_date": "2026-06-27",
        "buffer": 0.05,  # Buffer % dependant on route length
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
    # BBox: Bounding Box
    # ABBox: Aligned Bounding Box
    # possible additons: Ellipsoid

    timer = Timer()

    # get initial shape of ROI
    init_roi = ROISelectorFactory.create(scenario, "BBox")

    roi_creation_time = timer.stop()

    # Set weather API data
    timer = Timer()
    weather_constraint = WeatherConstraint()
    weather_constraint.fetch_weather(
        grid_df=init_roi.roi_df,
        start_date=scenario.constraints["start_date"],
        end_date=scenario.constraints["end_date"]
    )
    weather_request_time = timer.stop()
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] <= 0.6])
    # )
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] > 0.6])
    # )
    # print(weather_constraint.weather_df["precipitation"].max())

    # ROI generation/iteration
    # what it does?
    # class - takes start_roi & weather_constraints & scenario as input
    # either start-now or timeframe based calculation
    # has functions:
    # - iterate - always does 1 iteration step, whereas the first iteration step is the initial generation
    # - run_iterations - runs multiple iteration steps or until failure
    # - helper functions that are getting called in the iterate function
    # - stores every iteration step inside the class as metadata
    roi_iterator = ROIIterator(
        initial_roi=init_roi,
        constraints={"weather_constraint": weather_constraint},
        scenario=scenario,
        mode=scenario.constraints["mode"],
    )
    # default 5 runs - each run -0.1 precipitation
    # all steps are saved in the class roi_iterator
    timer = Timer()
    roi = roi_iterator.run_iterations(n=30)
    iteration_time = timer.stop()

    # use mechanic like to_simple_polygon to get roi in a single polygon without interiors
    if roi.interiors != 0:
        roi2 = to_simple_polygon(roi)
    # plot test
    reachable_df = reachable(
        df=weather_constraint.weather_df.copy(),
        start=scenario.start,
        departure_time=departure_time,
        avg_speed=80,
    )
    # print(len(reachable_df[reachable_df["precipitation"] <= roi_iterator.threshold]))
    # print(len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold]))
    #
    # departure_time = pd.Timestamp("2026-06-26 7:00")
    # reachable_df["precipitation"].max()
    # len(roi.interiors)

    # plot_roi_result(
    #     reachable_df,
    #     init_roi.roi_df,
    #     roi,
    #     start,
    #     goal,
    #     roi_iterator.threshold
    # )
    # # plot the simple polygon which can be given to the API
    # if roi.interiors != 0:
    #     plot_roi_result(
    #         reachable_df,
    #         init_roi.roi_df,
    #         roi2,
    #         start,
    #         goal,
    #         roi_iterator.threshold
    #     )

    # departure_time = pd.Timestamp("2026-06-27 0:00")
    # maximum_rain_points = 0
    # searched_departure = None
    # for i in range(48):
    #     reachable_df = reachable(
    #         df=weather_constraint.weather_df.copy(),
    #         start=scenario.start,
    #         departure_time=departure_time,
    #         avg_speed=80,
    #     )
    #     if maximum_rain_points < len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold]):
    #         maximum_rain_points = len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold])
    #         searched_departure = departure_time
    #     departure_time = departure_time + timedelta(hours=1)

    roi_gdf = gpd.GeoDataFrame(
        geometry=[roi],
        crs="EPSG:4326"
    )
    # metrics
    (
        initial_area,
        final_area,
        roi_reduction,
        remaining_area,
    ) = roi_metrics(init_roi.roi_df.to_crs("EPSG:3035"), roi_gdf.to_crs("EPSG:3035"))

    (
        reachable_points,
        satisfying_points,
        violating_points,
        constraint_satisfaction,
    ) = constraint_metrics(
        reachable_df,
        0,
    )

    result = EvaluationResult(
        scenario="No Rain",

        # -----------------------------
        # Runtime
        # -----------------------------
        roi_creation_time=roi_creation_time,
        weather_request_time=weather_request_time,
        iteration_time=iteration_time,
        total_runtime=(
                roi_creation_time
                + weather_request_time
                + iteration_time
        ),

        # -----------------------------
        # ROI
        # -----------------------------
        initial_area=initial_area[0],
        final_area=final_area[0],
        roi_reduction=roi_reduction[0],
        remaining_area=remaining_area[0],

        # -----------------------------
        # Constraint Satisfaction
        # -----------------------------
        reachable_points=reachable_points,
        satisfying_points=int(satisfying_points),
        violating_points=int(violating_points),
        constraint_satisfaction=float(constraint_satisfaction),

        # -----------------------------
        # Iteration
        # -----------------------------
        iterations=roi_iterator.iteration,
        final_threshold=roi_iterator.threshold,
        holes=len(roi.interiors),
        connected=True,

        departure_time=str(departure_time),
    )

    result.print_summary()


def scenario_heavy_rain():
    """
    Heavy rain corridor -> expected: threshold reduces and eventually stops
    """
    start = (52.5200, 13.4050)  # Berlin
    goal = (48.8566, 2.3522)  # Paris

    # has to be in the start_date and ebd_date timeframes
    departure_time = pd.Timestamp("2026-06-27 16:00")

    # https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?lv2=101812&lv3=101906&utm_source=chatgpt.com
    # precipitation thresholds:
    # 0 < x < 2,5 mm light rain
    # 2,5 <= x < 10 mm medium rain
    # 10 <= x < 50 mm heavy rain
    # 50 <= x mm very heavy rain (flooding expected)
    constraints = {
        # maximum precipitation in mm
        "max_rain": 3,
        # has to be in range 3 month before TODAY
        "start_date": "2026-06-27",
        # has to be in range 15 days after TODAY
        "end_date": "2026-06-30",
        "buffer": 0.05,  # Buffer % dependant on route length
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
    # BBox: Bounding Box
    # ABBox: Aligned Bounding Box
    # possible additons: Ellipsoid

    timer = Timer()

    # get initial shape of ROI
    init_roi = ROISelectorFactory.create(scenario, "BBox")

    roi_creation_time = timer.stop()

    # Set weather API data
    timer = Timer()
    weather_constraint = WeatherConstraint()
    weather_constraint.fetch_weather(
        grid_df=init_roi.roi_df,
        start_date=scenario.constraints["start_date"],
        end_date=scenario.constraints["end_date"]
    )
    weather_request_time = timer.stop()
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] <= 0.6])
    # )
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] > 0.6])
    # )
    # print(weather_constraint.weather_df["precipitation"].max())

    # ROI generation/iteration
    # what it does?
    # class - takes start_roi & weather_constraints & scenario as input
    # either start-now or timeframe based calculation
    # has functions:
    # - iterate - always does 1 iteration step, whereas the first iteration step is the initial generation
    # - run_iterations - runs multiple iteration steps or until failure
    # - helper functions that are getting called in the iterate function
    # - stores every iteration step inside the class as metadata
    roi_iterator = ROIIterator(
        initial_roi=init_roi,
        constraints={"weather_constraint": weather_constraint},
        scenario=scenario,
        mode=scenario.constraints["mode"],
    )
    # default 5 runs - each run -0.1 precipitation
    # all steps are saved in the class roi_iterator
    timer = Timer()
    roi = roi_iterator.run_iterations(n=30)
    iteration_time = timer.stop()

    # use mechanic like to_simple_polygon to get roi in a single polygon without interiors
    if roi.interiors != 0:
        roi2 = to_simple_polygon(roi)
    # plot test
    reachable_df = reachable(
        df=weather_constraint.weather_df.copy(),
        start=scenario.start,
        departure_time=departure_time,
        avg_speed=80,
    )
    # print(len(reachable_df[reachable_df["precipitation"] <= roi_iterator.threshold]))
    # print(len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold]))

    # departure_time = pd.Timestamp("2026-06-28 1:00")
    # reachable_df["precipitation"].max()
    # len(roi.interiors)

    # plot_roi_result(
    #     reachable_df,
    #     init_roi.roi_df,
    #     roi,
    #     start,
    #     goal,
    #     roi_iterator.threshold
    # )
    # # plot the simple polygon which can be given to the API
    # if roi.interiors != 0:
    #     plot_roi_result(
    #         reachable_df,
    #         init_roi.roi_df,
    #         roi2,
    #         start,
    #         goal,
    #         roi_iterator.threshold
    #     )

    # departure_time = pd.Timestamp("2026-06-27 0:00")
    # maximum_rain_points = 0
    # searched_departure = None
    # for i in range(48):
    #     reachable_df = reachable(
    #         df=weather_constraint.weather_df.copy(),
    #         start=scenario.start,
    #         departure_time=departure_time,
    #         avg_speed=80,
    #     )
    #     if maximum_rain_points < len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold]):
    #         maximum_rain_points = len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold])
    #         searched_departure = departure_time
    #     departure_time = departure_time + timedelta(hours=1)

    roi_gdf = gpd.GeoDataFrame(
        geometry=[roi],
        crs="EPSG:4326"
    )
    # metrics
    (
        initial_area,
        final_area,
        roi_reduction,
        remaining_area,
    ) = roi_metrics(init_roi.roi_df.to_crs("EPSG:3035"), roi_gdf.to_crs("EPSG:3035"))

    (
        reachable_points,
        satisfying_points,
        violating_points,
        constraint_satisfaction,
    ) = constraint_metrics(
        reachable_df,
        0,
    )

    result = EvaluationResult(
        scenario="Heavy Rain",

        # -----------------------------
        # Runtime
        # -----------------------------
        roi_creation_time=roi_creation_time,
        weather_request_time=weather_request_time,
        iteration_time=iteration_time,
        total_runtime=(
                roi_creation_time
                + weather_request_time
                + iteration_time
        ),

        # -----------------------------
        # ROI
        # -----------------------------
        initial_area=initial_area[0],
        final_area=final_area[0],
        roi_reduction=roi_reduction[0],
        remaining_area=remaining_area[0],

        # -----------------------------
        # Constraint Satisfaction
        # -----------------------------
        reachable_points=reachable_points,
        satisfying_points=int(satisfying_points),
        violating_points=int(violating_points),
        constraint_satisfaction=float(constraint_satisfaction),

        # -----------------------------
        # Iteration
        # -----------------------------
        iterations=roi_iterator.iteration,
        final_threshold=roi_iterator.threshold,
        holes=len(roi.interiors),
        connected=True,

        departure_time=str(departure_time),
    )

    result.print_summary()


def scenario_no_feasible_connection():
    """
    No feasible connection -> expected: previous valid ROI returned
    """
    """
        Heavy rain corridor -> expected: threshold reduces and eventually stops
        """
    start = (52.5200, 13.4050)  # Berlin
    goal = (48.8566, 2.3522)  # Paris

    # has to be in the start_date and ebd_date timeframes
    departure_time = pd.Timestamp("2026-06-26 7:00")

    # https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?lv2=101812&lv3=101906&utm_source=chatgpt.com
    # precipitation thresholds:
    # 0 < x < 2,5 mm light rain
    # 2,5 <= x < 10 mm medium rain
    # 10 <= x < 50 mm heavy rain
    # 50 <= x mm very heavy rain (flooding expected)
    constraints = {
        # maximum precipitation in mm
        "max_rain": 3,
        # has to be in range 3 month before TODAY
        "start_date": "2026-06-25",
        # has to be in range 15 days after TODAY
        "end_date": "2026-06-27",
        "buffer": 0.05,  # Buffer % dependant on route length
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
    # BBox: Bounding Box
    # ABBox: Aligned Bounding Box
    # possible additons: Ellipsoid

    timer = Timer()

    # get initial shape of ROI
    init_roi = ROISelectorFactory.create(scenario, "BBox")

    roi_creation_time = timer.stop()

    # Set weather API data
    timer = Timer()
    weather_constraint = WeatherConstraint()
    weather_constraint.fetch_weather(
        grid_df=init_roi.roi_df,
        start_date=scenario.constraints["start_date"],
        end_date=scenario.constraints["end_date"]
    )
    weather_request_time = timer.stop()
    # create artificial rain barrier
    weather_constraint.weather_df = create_rain_barrier(
        weather_constraint.weather_df,
        lat_min=40.5,
        lat_max=53.5,
        lon_min=5.0,
        lon_max=10.0,
        precipitation_value=100
    )
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] <= 0.6])
    # )
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] > 0.6])
    # )
    # print(weather_constraint.weather_df["precipitation"].max())

    # ROI generation/iteration
    # what it does?
    # class - takes start_roi & weather_constraints & scenario as input
    # either start-now or timeframe based calculation
    # has functions:
    # - iterate - always does 1 iteration step, whereas the first iteration step is the initial generation
    # - run_iterations - runs multiple iteration steps or until failure
    # - helper functions that are getting called in the iterate function
    # - stores every iteration step inside the class as metadata
    roi_iterator = ROIIterator(
        initial_roi=init_roi,
        constraints={"weather_constraint": weather_constraint},
        scenario=scenario,
        mode=scenario.constraints["mode"],
    )
    # default 5 runs - each run -0.1 precipitation
    # all steps are saved in the class roi_iterator
    timer = Timer()
    roi = roi_iterator.run_iterations(n=30)
    iteration_time = timer.stop()

    # use mechanic like to_simple_polygon to get roi in a single polygon without interiors
    if roi.interiors != 0:
        roi2 = to_simple_polygon(roi)
    # plot test
    reachable_df = reachable(
        df=weather_constraint.weather_df.copy(),
        start=scenario.start,
        departure_time=departure_time,
        avg_speed=80,
    )
    # print(len(reachable_df[reachable_df["precipitation"] <= roi_iterator.threshold]))
    # print(len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold]))

    # departure_time = pd.Timestamp("2026-06-28 1:00")
    # reachable_df["precipitation"].max()
    # len(roi.interiors)

    # plot_roi_result(
    #     reachable_df,
    #     init_roi.roi_df,
    #     roi,
    #     start,
    #     goal,
    #     roi_iterator.threshold
    # )
    # # plot the simple polygon which can be given to the API
    # if roi.interiors != 0:
    #     plot_roi_result(
    #         reachable_df,
    #         init_roi.roi_df,
    #         roi2,
    #         start,
    #         goal,
    #         roi_iterator.threshold
    #     )

    # departure_time = pd.Timestamp("2026-06-27 0:00")
    # maximum_rain_points = 0
    # searched_departure = None
    # for i in range(48):
    #     reachable_df = reachable(
    #         df=weather_constraint.weather_df.copy(),
    #         start=scenario.start,
    #         departure_time=departure_time,
    #         avg_speed=80,
    #     )
    #     if maximum_rain_points < len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold]):
    #         maximum_rain_points = len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold])
    #         searched_departure = departure_time
    #     departure_time = departure_time + timedelta(hours=1)

    # metrics
    (
        initial_area,
        final_area,
        roi_reduction,
        remaining_area,
    ) = roi_metrics(init_roi.roi_df.to_crs("EPSG:3035"), roi.to_crs("EPSG:3035"))

    (
        reachable_points,
        satisfying_points,
        violating_points,
        constraint_satisfaction,
    ) = constraint_metrics(
        reachable_df,
        0,
    )

    result = EvaluationResult(
        scenario="No Feasible Connection",

        # -----------------------------
        # Runtime
        # -----------------------------
        roi_creation_time=roi_creation_time,
        weather_request_time=weather_request_time,
        iteration_time=iteration_time,
        total_runtime=(
                roi_creation_time
                + weather_request_time
                + iteration_time
        ),

        # -----------------------------
        # ROI
        # -----------------------------
        initial_area=initial_area[0],
        final_area=final_area[0],
        roi_reduction=roi_reduction[0],
        remaining_area=remaining_area[0],

        # -----------------------------
        # Constraint Satisfaction
        # -----------------------------
        reachable_points=reachable_points,
        satisfying_points=int(satisfying_points),
        violating_points=int(violating_points),
        constraint_satisfaction=float(constraint_satisfaction),

        # -----------------------------
        # Iteration
        # -----------------------------
        iterations=roi_iterator.iteration,
        final_threshold=3,
        holes=0,
        connected=True,

        departure_time=str(departure_time),
    )

    result.print_summary()


def scenario_different_departure():
    """
    over a timeframe show, that the selected time has the least precipitation.
    """
    start = (52.5200, 13.4050)  # Berlin
    goal = (48.8566, 2.3522)  # Paris

    # has to be in the start_date and ebd_date timeframes
    departure_time = pd.Timestamp("2026-06-27 16:00")

    # https://www.dwd.de/DE/service/lexikon/Functions/glossar.html?lv2=101812&lv3=101906&utm_source=chatgpt.com
    # precipitation thresholds:
    # 0 < x < 2,5 mm light rain
    # 2,5 <= x < 10 mm medium rain
    # 10 <= x < 50 mm heavy rain
    # 50 <= x mm very heavy rain (flooding expected)
    constraints = {
        # maximum precipitation in mm
        "max_rain": 3,
        # has to be in range 3 month before TODAY
        "start_date": "2026-06-27",
        # has to be in range 15 days after TODAY
        "end_date": "2026-06-28",
        "buffer": 0.05,  # Buffer % dependant on route length
        # departure // timeframe
        "mode": "timeframe",
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
    # BBox: Bounding Box
    # ABBox: Aligned Bounding Box
    # possible additons: Ellipsoid

    timer = Timer()

    # get initial shape of ROI
    init_roi = ROISelectorFactory.create(scenario, "BBox")

    roi_creation_time = timer.stop()

    # Set weather API data
    timer = Timer()
    weather_constraint = WeatherConstraint()
    weather_constraint.fetch_weather(
        grid_df=init_roi.roi_df,
        start_date=scenario.constraints["start_date"],
        end_date=scenario.constraints["end_date"]
    )
    weather_request_time = timer.stop()
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] <= 0.6])
    # )
    # print(
    #     len(weather_constraint.weather_df[weather_constraint.weather_df["precipitation"] > 0.6])
    # )
    # print(weather_constraint.weather_df["precipitation"].max())

    # ROI generation/iteration
    # what it does?
    # class - takes start_roi & weather_constraints & scenario as input
    # either start-now or timeframe based calculation
    # has functions:
    # - iterate - always does 1 iteration step, whereas the first iteration step is the initial generation
    # - run_iterations - runs multiple iteration steps or until failure
    # - helper functions that are getting called in the iterate function
    # - stores every iteration step inside the class as metadata
    roi_iterator = ROIIterator(
        initial_roi=init_roi,
        constraints={"weather_constraint": weather_constraint},
        scenario=scenario,
        mode=scenario.constraints["mode"],
    )
    # default 5 runs - each run -0.1 precipitation
    # all steps are saved in the class roi_iterator
    timer = Timer()
    roi = roi_iterator.run_iterations(n=30)
    iteration_time = timer.stop()

    # use mechanic like to_simple_polygon to get roi in a single polygon without interiors
    # if roi.interiors != 0:
    #     roi2 = to_simple_polygon(roi)
    # plot test
    # reachable_df = reachable(
    #     df=weather_constraint.weather_df.copy(),
    #     start=scenario.start,
    #     departure_time=pd.Timestamp(roi_iterator.departure_time),
    #     avg_speed=80,
    # )
    # print(len(reachable_df[reachable_df["precipitation"] <= roi_iterator.threshold]))
    # print(len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold]))

    # departure_time = pd.Timestamp("2026-06-28 1:00")
    # reachable_df["precipitation"].max()
    # len(roi.interiors)

    # plot_roi_result(
    #     reachable_df,
    #     init_roi.roi_df,
    #     roi,
    #     start,
    #     goal,
    #     roi_iterator.threshold
    # )
    # # plot the simple polygon which can be given to the API
    # if roi.interiors != 0:
    #     plot_roi_result(
    #         reachable_df,
    #         init_roi.roi_df,
    #         roi2,
    #         start,
    #         goal,
    #         roi_iterator.threshold
    #     )

    # departure_time = pd.Timestamp("2026-06-27 0:00")
    # maximum_rain_points = 0
    # searched_departure = None
    # for i in range(48):
    #     reachable_df = reachable(
    #         df=weather_constraint.weather_df.copy(),
    #         start=scenario.start,
    #         departure_time=departure_time,
    #         avg_speed=80,
    #     )
    #     if maximum_rain_points < len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold]):
    #         maximum_rain_points = len(reachable_df[reachable_df["precipitation"] > roi_iterator.threshold])
    #         searched_departure = departure_time
    #     departure_time = departure_time + timedelta(hours=1)

    # metrics
    departure_results = evaluate_departure_times(
        weather_constraint.weather_df,
        start,
        pd.Timestamp("2026-06-27 00:00"),
        hours=24,
    )

    best_departure = departure_results.loc[
        departure_results["total_precipitation"].idxmin()
    ]

    selected_departure = roi_iterator.departure_time

    selected_precipitation = departure_results[
        departure_results["departure_time"]
        == selected_departure
        ]["total_precipitation"].iloc[0]

    best_precipitation = best_departure["total_precipitation"]

    departure_accuracy = (
            best_precipitation /
            selected_precipitation
    )

    EvaluationResult.print_summary_different_departure(
        selected_departure=selected_departure,
        best_departure=best_departure.departure_time,
        selected_precipitation=selected_precipitation,
        best_precipitation=best_precipitation,
        departure_selection_accuracy=departure_accuracy,
    )