from shapely.lib import unary_union

from utils.geometry import reachable, haversine
                            #, precipitation_regions, find_region, same_region, to_simple_polygon
from shapely.geometry import box
from datetime import datetime, timedelta
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
        self.iteration = 0
        self.iteration_roi = initial_roi
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
            # filter weather constraint
            df = df[df["precipitation"] < threshold]
            departure_time = self.scenario.departure_time

        elif self.mode == "timeframe":
            timeframes = self.generate_timeframes()
            # filter weather constraint
            filtered = df[df["precipitation"] < threshold]
            # get the best timeframe based on precipitation sum in the timeframe
            df, best_window = self._select_best_timeframe(filtered, timeframes)
            # best_window is a (start, end) tuple
            departure_time = best_window[0]

        else:
            raise ValueError(f"Invalid mode '{self.mode}'. Expected 'timeframe' or 'departure'.")

        # depending on departure time use an approximation which points to keep
        reachable_df = df[
            df.apply(
                reachable,
                axis=1,
                args=(
                    self.scenario.start,
                    self.scenario.goal,
                    departure_time,
                ),
                avg_speed=80
            )
        ]

        # build grid squares with 5% tolerance
        side = self.constraints.weather_constraint.spacing * 1.05
        half = side / 2

        cells = [
            box(lon - half, lat - half, lon + half, lat + half)
            for lat, lon in zip(reachable_df["lat"], reachable_df["lon"])
        ]

        if not cells:
            return None

        # merge
        merged = unary_union(cells)
        return merged


    def run_iterations(self, df=None, start_poly=None, n=5):
        """Perform multiple iteration steps."""

        if start_poly is None:
            start_poly = self.iteration_roi
        if df is None:
            df = self.constraints.weather_constraint.weather_df
        roi = start_poly
        for i in range(n):
            iteration = i+1
            threshold = self._dynamic_threshold(i)

            new_roi = self.iterate(df, threshold)

            roi = self._ensure_connected(new_roi)
            if roi is None:
                print(f"Iteration {iteration} was not connected.")
                break
            self.iteration += 1
            self._update_roi(roi)
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
        threshold = self.scenario.max_rain * (0.9 ** i)
        return threshold

    def _ensure_connected(self, roi):
        """
        Keep only component containing A (and optionally B).
        """

        polygons = getattr(roi, "geoms", [roi])

        for poly in polygons:
            if poly.covers(self.scenario.start) and poly.covers(self.scenario.goal):
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
    def _select_best_timeframe(self, df, timeframes):
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
            self.scenario.end[0],
            self.scenario.end[1],
        ) / avg_speed)

        # ensure datetime
        start_date = datetime.fromisoformat(self.scenario.constraints["start_date"])
        end_date = datetime.fromisoformat(self.scenario.constraints["end_date"])

        # round everything to full hour
        start_date = start_date.replace(minute=0, second=0, microsecond=0)
        end_date = end_date.replace(minute=0, second=0, microsecond=0)

        delta = timedelta(hours=1)

        timeframes = []

        current = start_date

        # last valid start so that end stays inside range
        last_start = end_date - timedelta(hours=travel_time_hours)

        while current <= last_start:
            timeframes.append(
                (current, current + timedelta(hours=travel_time_hours))
            )
            current += delta

        return timeframes
