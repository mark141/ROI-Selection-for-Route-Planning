# geometry utility functions

import numpy as np
import pandas as pd
import geopandas as gpd
import math
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import nearest_points, transform
from pyproj import Transformer
from geopy.distance import geodesic


def grid_points_in_polygon(polygon, target_count):
    """
    Stable square-grid (fishnet) generator in projected CRS.
    Produces ~target_count equidistant points.
    """
    to_utm = Transformer.from_crs(
        "EPSG:4326", "EPSG:32632", always_xy=True
    ).transform
    to_wgs = Transformer.from_crs(
        "EPSG:32632", "EPSG:4326", always_xy=True
    ).transform
    polygon_utm = transform(to_utm, polygon)
    # Get bounds of the polygon
    minx, miny, maxx, maxy = polygon_utm.bounds

    # Estimate initial spacing from area and target count in m² and m
    area = polygon_utm.area
    spacing = np.sqrt(area / target_count)

    # Build grid in bounding box
    xs = np.arange(minx, maxx, spacing)
    ys = np.arange(miny, maxy, spacing)
    # xx, yy = np.meshgrid(xs, ys)
    pts = [Point(x, y) for x in xs for y in ys if polygon_utm.contains(Point(x, y))]

    #
    if len(pts) > target_count:
        step = len(pts) / target_count
        pts = [pts[int(i*step)] for i in range(target_count)]

    # return to EPSG:4326
    pts_inside = [transform(to_wgs, p) for p in pts]
    # Build GeoDataFrame
    gdf = gpd.GeoDataFrame(
        geometry=pts_inside,
        crs="EPSG:4326"
    )

    return gdf, spacing


def build_oriented_rectangle(
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


def haversine(lat1, lon1, lat2, lon2) -> float:
    """
    Calculate the haversine distance between two points.
    :param lat1: latitude of first point
    :param lon1: longitude of first point
    :param lat2: latitude of second point
    :param lon2: longitude of second point
    :return: distance between two points in km
    """
    r = 6371.0  # km

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return r * c


def reachable(df, start, departure_time, avg_speed=80):
    """
    Filter weather points to those that are expected to be reached at their corresponding weather timestamp.

    For each weather point, the geodesic distance from the start location is computed. Assuming a constant average
    driving speed, an expected arrival time is assigned in one-hour intervals:

    - Points within `avg_speed` km are assigned `departure_time`.
    - Points between `avg_speed` and `2 * avg_speed` km are assigned departure_time + 1 hour`.
    - Each additional `avg_speed` km increases the expected arrival time by one hour.

    Only rows where the computed expected arrival time exactly matches the weather observation time are returned.

    :param df: pd.DataFrame containing at least the columns `time`, `lat`, and `lon`.
    :param start: Tuple `(lat, lon)` representing the departure location.
    :param departure_time: Departure timestamp.
    :param avg_speed: Assumed constant driving speed in km/h. Defaults to 80.
    :return: pd.DataFrame containing only the weather points that are expected
    to be reached at the corresponding observation time.
    """
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    departure_time = pd.to_datetime(departure_time).round("h")

    # compute distance
    df["dist_start"] = df.apply(
        lambda r: geodesic(start, (r["lat"], r["lon"])).km,
        axis=1
    )

    # give each point an expected arrival time for discrete selection
    hour_offset = np.ceil(df["dist_start"] / avg_speed).astype(int) - 1
    hour_offset = hour_offset.clip(lower=0)
    df["expected_time"] = departure_time + pd.to_timedelta(hour_offset, unit="h")

    # only take weather data points that are reachable from our start location
    df = df[df["expected_time"] == df["time"]]

    return df


def to_simple_polygon(poly):
    """
    Convert a Polygon with holes into a Polygon with a single exterior ring
    by connecting every hole to the exterior with a zero-width bridge.
    """

    def _rotate_ring(coords, point):
        """
        Rotate a closed ring so that it starts at the vertex closest to `point`.
        """
        coords = list(coords[:-1])  # remove duplicate closing vertex

        idx = min(
            range(len(coords)),
            key=lambda i: (coords[i][0] - point.x) ** 2 + (coords[i][1] - point.y) ** 2,
        )

        rotated = coords[idx:] + coords[:idx]
        rotated.append(rotated[0])
        return rotated

    def _insert_point(ring, point):
        """
        Insert point as first vertex if it is not already there.
        """
        p = (point.x, point.y)

        if ring[0] != p:
            ring = [p] + ring

        return ring


    exterior = list(poly.exterior.coords[:-1])

    for interior in poly.interiors:

        hole = LineString(interior)
        outer = LineString(exterior + [exterior[0]])

        p_outer, p_hole = nearest_points(outer, hole)

        # rotate both rings so bridge endpoints become first vertices
        ext = _rotate_ring(outer.coords, p_outer)
        hol = _rotate_ring(interior.coords, p_hole)

        ext = _insert_point(ext, p_outer)
        hol = _insert_point(hol, p_hole)

        # remove duplicated closing coordinate
        ext = ext[:-1]
        hol = hol[:-1]

        # splice hole into exterior
        exterior = (
            ext[:1]
            + hol
            + [hol[0]]
            + [ext[0]]
            + ext[1:]
        )

    exterior.append(exterior[0])

    return Polygon(exterior)