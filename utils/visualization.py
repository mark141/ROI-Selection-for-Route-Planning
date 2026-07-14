# plot visualization

import geopandas as gpd
import contextily as cx
import matplotlib.pyplot as plt
from shapely.geometry import Point


def plot_roi_result(weather_gdf, init_roi, roi, start, goal, max_rain):
    """
    Plots the initial roi, the calculated roi, the points for the weather colored based on max rain precipitation,
    the start and goal of the route.
    """
    weather_gdf = gpd.GeoDataFrame(
        weather_gdf,
        geometry=[Point(lon, lat) for lon, lat in zip(weather_gdf["lon"], weather_gdf["lat"])],
        crs="EPSG:4326"
    )
    dry_weather = weather_gdf[weather_gdf["precipitation"] < max_rain]
    wet_weather = weather_gdf[weather_gdf["precipitation"] >= max_rain]
    # Convert to Web Mercator
    dry_weather = dry_weather.to_crs(epsg=3857)
    wet_weather = wet_weather.to_crs(epsg=3857)
    init_roi = init_roi.to_crs(epsg=3857)

    # Convert ROI polygon
    roi_gdf = gpd.GeoDataFrame(
        geometry=[roi],
        crs="EPSG:4326"
    )

    roi_gdf = roi_gdf.to_crs(epsg=3857)

    # Start/goal points
    start_gdf = gpd.GeoDataFrame(
        geometry=[Point(start[1], start[0])],
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    goal_gdf = gpd.GeoDataFrame(
        geometry=[Point(goal[1], goal[0])],
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 10))

    # ROI
    roi_gdf.plot(
        ax=ax,
        facecolor="lightblue",
        edgecolor="black",
        alpha=0.3,
        label="ROI",
    )

    # Init ROI
    init_roi.plot(
        ax=ax,
        facecolor="yellow",
        edgecolor="black",
        alpha=0.1,
        label="Init ROI"
    )

    # Dry weather points
    if len(dry_weather) > 0:
        dry_weather.plot(
            ax=ax,
            color="green",
            markersize=12,
            label=f"Precipitation in mm < {max_rain:.2f}"
        )

    # Wet weather points
    if len(wet_weather) > 0:
        wet_weather.plot(
            ax=ax,
            color="red",
            markersize=12,
            label=f"Precipitation in mm >= {max_rain:.2f}"
        )

    # Start
    start_gdf.plot(
        ax=ax,
        color="green",
        markersize=80,
        marker="o",
        label="Start"
    )

    # Goal
    goal_gdf.plot(
        ax=ax,
        color="blue",
        markersize=80,
        marker="x",
        label="Goal"
    )

    # Add basemap
    cx.add_basemap(
        ax,
        source=cx.providers.OpenStreetMap.Mapnik,
        zoom=8
    )

    ax.legend()
    ax.set_axis_off()

    plt.show()