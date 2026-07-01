# geometry utility functions
import numpy as np
import geopandas as gpd
import math
from shapely.geometry import box, LineString, Polygon, Point
from shapely.ops import nearest_points, unary_union
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
    Generate a grid of equidistant points within the polygon,
    then return approximately target_count points inside it.

    Args:
        polygon (shapely.geometry.Polygon): The polygon to fill.
        target_count (int): Desired number of points.

    Returns:
        geopandas.GeoDataFrame: Points inside polygon (approx N).
        spacing: spacing between points in degrees.
    """
    # Get bounds of the polygon
    minx, miny, maxx, maxy = polygon.bounds

    # Estimate initial spacing from area and target count
    area = polygon.area
    spacing = np.sqrt(area / target_count)

    # Adjust grid spacing until ~target_count available
    for _ in range(100):  # max iterations to converge
        # Build grid in bounding box
        xs = np.arange(minx, maxx, spacing)
        ys = np.arange(miny, maxy, spacing)
        xx, yy = np.meshgrid(xs, ys)
        pts = [Point(x, y) for x, y in zip(xx.ravel(), yy.ravel())]

        # Keep only points inside polygon
        pts_inside = [p for p in pts if polygon.contains(p)]

        # Check how many we have
        n = len(pts_inside)
        if abs(n - target_count) < target_count * 0.10:
            # Good enough (within 10%)
            break

        # Adjust spacing based on difference
        spacing *= np.sqrt(n / target_count)

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
def reachable(row, start, dest, departure_time, avg_speed=80):
    """
    Determine whether a weather point is reachable from the trip origin at
    the given timestamp using a constant average driving speed.

     A weather point is considered reachable if:
      1. Its distance from the start location is less than or equal to the
         maximum distance that could have been driven since `departure_time`.
      2. It is closer to the destination than the start location, preventing
         points located behind the direction of travel from being selected.

    :param row: pd.Series - A row from the weather DataFrame containing at least the columns `time`, `lat`, and `lon`.
    :param start: (tuple[float, float]) - Latitude and longitude of the departure location as `(lat, lon)`.
    :param dest: (tuple[float, float]) - Latitude and longitude of the destination as `(lat, lon)`.
    :param departure_time: pd.Series - The timestamp of the departure location as `time`.
    :param avg_speed: (float, optional) - Assumed constant driving speed in km/h. Defaults to 80.
    :return: bool - `True` if the weather point is considered reachable at the given time, otherwise `False`.
    """

    start_to_dest = geodesic(start, dest).km
    hours = (row["time"] - departure_time).total_seconds() / 3600

    if hours < 0:
        return False

    radius = hours * avg_speed

    point = (row["lat"], row["lon"])

    dist_from_start = geodesic(start, point).km
    dist_to_dest = geodesic(point, dest).km

    return (
        dist_from_start<= radius and
        dist_to_dest < start_to_dest
    )


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