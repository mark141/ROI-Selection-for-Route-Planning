# geometry utility functions
import numpy as np
import pandas as pd
import geopandas as gpd
import math
from shapely.geometry import box, LineString, Polygon, Point
from shapely.ops import nearest_points, unary_union, transform
from pyproj import Transformer
from typing import Tuple, List
from geopy.distance import geodesic


def interpolate_points(
    start: Tuple[float, float],
    goal: Tuple[float, float],
    steps: int = 50
) -> List[Tuple[float, float]]:

    latitudes = np.linspace(start[0], goal[0], steps)
    longitudes = np.linspace(start[1], goal[1], steps)

    return list(zip(latitudes, longitudes))


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


# use this with : reachable_df = df[df.apply(reachable, axis=1)]
def reachable(df, start, dest, departure_time, avg_speed=80):
    """
    Determine whether a weather point is reachable from the trip origin at
    the given timestamp using a constant average driving speed.

     A weather point is considered reachable if:
      1. Its distance from the start location is less than or equal to the
         maximum distance that could have been driven since `departure_time`.
      2. It is closer to the destination than the start location, preventing
         points located behind the direction of travel from being selected.

    :param df: pd.Dataframe - A row from the weather DataFrame containing at least the columns `time`, `lat`, and `lon`.
    :param start: (tuple[float, float]) - Latitude and longitude of the departure location as `(lat, lon)`.
    :param dest: (tuple[float, float]) - Latitude and longitude of the destination as `(lat, lon)`.
    :param departure_time: pd.Timestamp - The timestamp of the departure location as `time`.
    :param avg_speed: (float, optional) - Assumed constant driving speed in km/h. Defaults to 80.
    :return: bool - `True` if the weather point is considered reachable at the given time, otherwise `False`.
    """
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    departure_time = pd.to_datetime(departure_time)

    # time diff in hours vectorized
    df["hours"] = (df["time"] - departure_time).dt.total_seconds() / 3600

    # remove future-negative times
    df = df[df["hours"] >= 0]

    df["time_bin"] = df["hours"].astype(int)

    start_to_dest = geodesic(start, dest).km

    # compute distances
    df["dist_start"] = df.apply(
        lambda r: geodesic(start, (r["lat"], r["lon"])).km,
        axis=1
    )
    df["dist_dest"] = df.apply(
        lambda r: geodesic((r["lat"], r["lon"]), dest).km,
        axis=1
    )

    # reachability constraints
    df = df[df["dist_dest"] < start_to_dest]

    # add 5% deviation
    df["max_reach"] = df["hours"] * avg_speed * 1.05
    df = df[df["dist_start"] <= df["max_reach"]]

    # keep only earliest bin per location
    idx = df.groupby(["lat", "lon"])["time_bin"].idxmin()
    df = df.loc[idx].reset_index(drop=True)

    return df


def precipitation_regions(df, max_precip, spacing_deg):
    # keep only "good" weather cells
    df = df[df["precipitation"] < max_precip].copy()

    # increase spacing by 5 %
    side = spacing_deg * 1.05
    half = side / 2

    # create one square per weather point
    geometry = [
        box(
            lon - half,
            lat - half,
            lon + half,
            lat + half,
        )
        for lat, lon in zip(df["lat"], df["lon"])
    ]

    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # merge touching/overlapping squares
    merged = gdf.geometry.union_all()      # GeoPandas >=1.1
    # alternatively: gdf.geometry.unary_union

    return merged


def find_region(regions, point):
    """
    Return the polygon containing the given point, or None if the point
    is not contained in any region.

    :param regions: Polygon | MultiPolygon
        Connected regions.
    :param point: tuple[float, float]
        (lat, lon)
    """
    # (lon, lat)
    point = Point(point[1], point[0])

    polygons = getattr(regions, "geoms", [regions])

    for poly in polygons:
        if poly.covers(point):
            return poly

    return None


def same_region(regions, point_a, point_b):
    """
    Return True if both points lie in the same connected region.

    :param regions: Polygon | MultiPolygon
        Connected precipitation regions.
    :param point_a: tuple[float, float]
        (lat, lon)
    :param point_b: tuple[float, float]
        (lat, lon)
    :return: boolean
    """
    region = find_region(regions, point_a)

    if region is None:
        return False

    return region.covers(Point(point_b[1], point_b[0]))


def to_simple_polygon(poly, bridge_width):
    """
    Convert a polygon with holes into a simple polygon by connecting every
    hole to the exterior using the smallest possible bridge.

    Parameters
    ----------
    poly : shapely.Polygon
    bridge_width : float
        Width of the bridge (e.g. 0.1 * weather_grid_spacing).

    Returns
    -------
    shapely.Polygon
    """
    result = poly

    while result.interiors:

        # take first remaining hole
        hole = LineString(result.interiors[0])

        # nearest points between hole and outer boundary
        p_outer, p_hole = nearest_points(result.exterior, hole)

        # create a narrow bridge
        bridge = LineString([p_outer, p_hole]).buffer(
            bridge_width / 2,
            cap_style="square"
        )

        # add the bridge to the polygon
        result = unary_union([result, bridge])

        # rebuild using only exterior
        result = Polygon(result.exterior)

    return result