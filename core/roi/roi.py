from core.interfaces.roi_selector import ROISelector
from utils.geometry import build_oriented_rectangle

import math
import numpy as np
import geopandas as gpd
from geopy.distance import geodesic
from shapely.geometry import box, Polygon


class BoundingBoxROISelector(ROISelector):

    def build_roi(self):
        start = self.scenario.start
        goal = self.scenario.goal

        # buffer as percentage (e.g. 0.05 = 5%)
        buffer_pct = self.scenario.constraints.get("buffer", 0.05)

        # geodesic distance in meters
        distance_m = geodesic(start, goal).meters

        # convert percentage to absolute buffer distance
        buffer_m = distance_m * buffer_pct

        start_lat, start_lon = start
        goal_lat, goal_lon = goal

        min_lat = min(start_lat, goal_lat)
        max_lat = max(start_lat, goal_lat)
        min_lon = min(start_lon, goal_lon)
        max_lon = max(start_lon, goal_lon)

        # meters -> degrees latitude
        lat_buffer = buffer_m / 111_320

        # meters -> degrees longitude
        mean_lat = (start_lat + goal_lat) / 2
        lon_buffer = buffer_m / (
            111_320 * max(0.01, abs(__import__("math").cos(__import__("math").radians(mean_lat))))
        )

        bbox = box(
            min_lon - lon_buffer,
            min_lat - lat_buffer,
            max_lon + lon_buffer,
            max_lat + lat_buffer,
        )

        self.roi_df = gpd.GeoDataFrame(
            {"type": ["BBox"]},
            geometry=[bbox],
            crs="EPSG:4326",
        )


class AlignedBoundingBoxROISelector(ROISelector):

    def build_roi(self):
        start_lat, start_lon = self.scenario.start
        goal_lat, goal_lon = self.scenario.goal

        buffer_pct = self.scenario.constraints.get("buffer", 0.05)

        # total distance between start and goal
        distance_m = geodesic(
            (start_lat, start_lon),
            (goal_lat, goal_lon)
        ).meters

        # extend rectangle in travel direction
        longitudinal_buffer = distance_m * buffer_pct

        # corridor width heuristic
        width_m = np.clip(
            distance_m * 0.25,
            50000,
            250000
        )

        self.roi_df = build_oriented_rectangle(
            start=(start_lat, start_lon),
            goal=(goal_lat, goal_lon),
            extension_m=longitudinal_buffer,
            width_m=width_m,
        )

    def _build_oriented_rectangle(
        self,
        start,
        goal,
        extension_m,
        width_m,
    ) -> gpd.GeoDataFrame:

        lat0 = (start[0] + goal[0]) / 2

        # local projection approximation
        meters_per_deg_lat = 111_320
        meters_per_deg_lon = (
            111_320 * math.cos(math.radians(lat0))
        )

        # convert to local metric coordinates
        sx = start[1] * meters_per_deg_lon
        sy = start[0] * meters_per_deg_lat

        gx = goal[1] * meters_per_deg_lon
        gy = goal[0] * meters_per_deg_lat

        # directional vector
        dx = gx - sx
        dy = gy - sy
        length = math.hypot(dx, dy)

        # normalized vector
        ux = dx / length
        uy = dy / length

        # perpendicular vector
        px = -uy
        py = ux

        # extend start and goal
        sx -= ux * extension_m
        sy -= uy * extension_m

        gx += ux * extension_m
        gy += uy * extension_m

        half_width = width_m / 2

        corners = [
            (
                sx + px * half_width,
                sy + py * half_width,
            ),
            (
                gx + px * half_width,
                gy + py * half_width,
            ),
            (
                gx - px * half_width,
                gy - py * half_width,
            ),
            (
                sx - px * half_width,
                sy - py * half_width,
            ),
        ]

        # back to lon/lat
        corners_ll = [
            (
                x / meters_per_deg_lon,
                y / meters_per_deg_lat,
            )
            for x, y in corners
        ]

        polygon = Polygon(corners_ll)

        return gpd.GeoDataFrame(
            {"type": ["ABBox"]},
            geometry=[polygon],
            crs="EPSG:4326",
        )


class ROISelectorFactory:

    @staticmethod
    def create(scenario, heuristic):

        selectors = {
            # BBox: Bounding Box
            "BBox": BoundingBoxROISelector,
            # ABBox: Aligned Bounding Box
            "ABBox": AlignedBoundingBoxROISelector,
            # CHull: Convex Hull
            # "CHull": ConvexHullROISelector,
            # BCorr: Buffered Corridor
            # "BCorr": BufferedCorridorROISelector,
        }

        try:
            return selectors[heuristic](scenario)
        except KeyError:
            raise ValueError(
                f"Unknown ROI heuristic '{heuristic}'"
            )