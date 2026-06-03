# gemoetry utility functions
import numpy as np
import geopandas as gpd
import math
from shapely.geometry import Polygon, Point
from typing import Tuple, List


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