from pyproj import Transformer
from utils.geometry import reachable, haversine#, precipitation_regions, find_region, same_region, to_simple_polygon
from shapely.ops import unary_union, transform
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection, Point
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import math



class ROIIterator:
    def __init__(
        self,
        initial_roi,
        constraints,
        scenario,
        mode="departure", # timeframe
    ):
        self.initial_roi = initial_roi
        # here only the weather constraints
        self.constraints = constraints
        # other constraints are in scenario
        self.scenario = scenario
        if mode not in {"timeframe", "departure"}:
            raise ValueError(
                f"Invalid mode '{mode}'. Expected 'timeframe' or 'departure'."
            )
        self.mode = mode
        self.departure_time = None
        # threshold after the iterations
        self.threshold = None
        self.iteration = 0
        self.iteration_roi = initial_roi.roi_df
        self.metadata = {
            "initial_roi": self.initial_roi,
            "constraints": self.constraints,
            "scenario": self.scenario,
            "mode": self.mode,
            "iteration": self.iteration,
            "iterations": {
                "00": self.initial_roi
            }
        }

    def iterate(self, df, threshold):
        """Perform a single ROI refinement step."""
        if self.mode == "departure":
            if self.departure_time is None:
                departure_time = self.scenario.constraints["departure_time"]
            else:
                departure_time = self.departure_time

        elif self.mode == "timeframe":
            timeframes = self.generate_timeframes()
            # get the best timeframe based on precipitation sum in the timeframe
            df, best_window = self._select_best_timeframe(df, timeframes)
            # best_window is a (start, end) tuple
            departure_time = best_window[0]

            # following interations are in the normal departure mode
            self.mode = "departure"
            self.departure_time = departure_time

        else:
            raise ValueError(f"Invalid mode '{self.mode}'. Expected 'timeframe' or 'departure'.")

        # filter weather constraint
        df = df[df["precipitation"] < threshold]
        # depending on departure time use an approximation which points to keep
        df["time"] = pd.to_datetime(df["time"])
        reachable_df = reachable(
            df,
            self.scenario.start,
            departure_time=departure_time,
            avg_speed=80,
        )

        # build grid squares with 25% tolerance - so they will merge with the unary_union
        spacing_m = self.constraints["weather_constraint"].spacing
        side = spacing_m * 1.25
        half = side / 2

        # EPSG transformations
        to_utm = Transformer.from_crs(
            "EPSG:4326",
            "EPSG:32632",
            always_xy=True,
        ).transform
        to_wgs84 = Transformer.from_crs(
            "EPSG:32632",
            "EPSG:4326",
            always_xy=True,
        ).transform

        cells = []
        for lat, lon in zip(reachable_df["lat"], reachable_df["lon"]):
            x, y = to_utm(lon, lat)
            cells.append(box(x - half, y - half, x + half, y + half))

        if not cells:
            return None

        # merge
        merged = unary_union(cells)
        return transform(to_wgs84, merged)


    def run_iterations(self, df=None, start_poly=None, n=5):
        """Perform multiple iteration steps."""

        if start_poly is None:
            start_poly = self.iteration_roi
        if df is None:
            df = self.constraints["weather_constraint"].weather_df
        roi = start_poly
        mode = self.mode
        for i in range(n):
            iteration = i+1
            threshold = self._dynamic_threshold(i)
            if threshold <= 0:
                print(f"Threshold is below 0 ({threshold}), stopping iteration {iteration}")
                break

            new_roi = self.iterate(df, threshold)
            # save iteration steps here already for validation
            self.iteration += 1
            self._update_roi(new_roi)
            new_roi = self._ensure_connected(new_roi)
            if new_roi is None:
                print(f"Iteration {iteration} was not connected.")
                break
            roi = new_roi
            self.threshold = threshold
        # set old mode for
        self.mode = mode
        print(f"{self.iteration} iterations done.")
        return roi

    def reset(self):
        """Reset to the initial ROI."""
        self.iteration = 0
        self.iteration_roi = self.initial_roi
        self.metadata = {
            "initial_roi": self.initial_roi,
            "constraints": self.constraints,
            "scenario": self.scenario,
            "mode": self.mode,
            "iteration": self.iteration,
            "iterations": {
                "00": self.initial_roi
            }
        }

    def _dynamic_threshold(self, i):
        threshold = self.scenario.constraints["max_rain"] - (0.1 * i)
        return threshold

    def _ensure_connected(self, roi):
        """
        Keep only component containing A (and optionally B).
        """
        if isinstance(roi, (Polygon, MultiPolygon)):
            polygons = getattr(roi, "geoms", [roi])
        elif isinstance(roi, GeometryCollection):
            polygons = list(roi.geoms)
        else:
            return None

        for poly in polygons:
            if poly.covers(Point(self.scenario.start[::-1])) and poly.covers(Point(self.scenario.goal[::-1])):
                return poly

        return None

    def _update_roi(self, roi):
        self.iteration_roi = roi
        # convert iteration to 2-digit string key
        key = str(self.iteration).zfill(2)
        # store ROI in metadata
        self.metadata["iterations"][key] = roi
        # also keep global iteration in metadata
        self.metadata["iteration"] = self.iteration

    @staticmethod
    def _select_best_timeframe(df, timeframes):
        """
        Select the best dataframe slice based on lowest total precipitation.

        Parameters
        ----------
        df : pd.DataFrame
            Must contain a 'time' and 'precipitation' column.
        timeframes : list[tuple]
            List of (start_time, end_time) tuples.

        Returns
        -------
        best_df : pd.DataFrame
            Filtered dataframe with the lowest total precipitation.
        best_window : tuple
            The (start, end) timeframe that was selected.
        """

        best_score = float("inf")
        best_df = None
        best_window = None
        df["time"] = pd.to_datetime(df["time"])

        for start, end in timeframes:
            filtered = df[(df["time"] >= start) & (df["time"] <= end)]

            if filtered.empty:
                continue

            score = filtered["precipitation"].sum()

            if score < best_score:
                best_score = score
                best_df = filtered
                best_window = (start, end)

        return best_df, best_window

    def generate_timeframes(self):
        """
        Generate hourly (start, end) timeframes clipped by travel time.
        """
        avg_speed = 80
        travel_time_hours = math.ceil(haversine(
            self.scenario.start[0],
            self.scenario.start[1],
            self.scenario.goal[0],
            self.scenario.goal[1],
        ) / avg_speed)

        # ensure datetime
        start_date = datetime.fromisoformat(self.scenario.constraints["start_date"])
        end_date = datetime.fromisoformat(self.scenario.constraints["end_date"])

        # round everything to full hour
        start_date = start_date.replace(minute=0, second=0, microsecond=0)
        end_date = end_date.replace(minute=0, second=0, microsecond=0)

        timeframes = []

        current = start_date

        # last valid start so that end stays inside range
        last_start = end_date - timedelta(hours=travel_time_hours)

        while current <= last_start:
            timeframes.append(
                (current, current + timedelta(hours=travel_time_hours))
            )
            current += timedelta(hours=1)

        return timeframes
