import requests
import geopandas as gpd
import pandas as pd

from core.base.constraint import Constraint
from utils.geometry import grid_points_in_polygon
from utils.dates import validate_date_range


class WeatherConstraint(Constraint):

    def __init__(self):
        self.weather_df = None
        self.spacing = None

    def fetch_weather(
            self,
            grid_df: gpd.GeoDataFrame,
            start_date: str,
            end_date: str,
        ):

        if not validate_date_range(start_date) or  not validate_date_range(end_date):
            raise ValueError("start_date and end_date must be within the allowed range: "
                             "from 3 months before today to 2 weeks after today.")

        # 200 Points is maximum for the API request.
        # but the more we get the better so always fit 200 points into the polygon shape
        grid_df, spacing = grid_points_in_polygon(grid_df.geometry.item(), 200)
        self.spacing = spacing

        # list of longitudes
        lon_str = ",".join(f"{pt.x:.5f}" for pt in grid_df.geometry)

        # list of latitudes
        lat_str = ",".join(f"{pt.y:.5f}" for pt in grid_df.geometry)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat_str,
            "longitude": lon_str,
            "hourly": "precipitation,temperature_2m,cloudcover",
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "Europe/Berlin",
        }

        response = requests.get(url, params=params, timeout=5)

        records = []
        for loc_resp in response.json():
            lat = loc_resp["latitude"]
            lon = loc_resp["longitude"]

            times = loc_resp["hourly"]["time"]
            prec = loc_resp["hourly"]["precipitation"]
            cloudcover = loc_resp["hourly"]["cloudcover"]
            temperature_2m = loc_resp["hourly"]["temperature_2m"]
            elevation = loc_resp["elevation"]

            for t_idx, t in enumerate(times):
                records.append({
                    "time": t,
                    "elevation": elevation,
                    "lat": lat,
                    "lon": lon,
                    "precipitation": prec[t_idx],
                    "precipitation_unit": "mm",
                    "cloudcover": cloudcover[t_idx],
                    "cloud_unit": "%",
                    "temperature_2m": temperature_2m[t_idx],
                    "teperature_2m_unit": "°C",
                })

        self.weather_df = pd.DataFrame(records)

    def evaluate(self, point, context):
        """
        Check if point is valid and return metadata for the point.
        :param point: tuple (lat, lon)
        :param context: dict
        :return: dict with metadata
        """
        lat, lon = point

        df = self.weather_df

        max_rain = context.get("max_rain")

        distances = (df["lat"] - lat) ** 2 + (df["lon"] - lon) ** 2
        clostest_idx = distances.idxmin()
        closest_row = df.loc[clostest_idx]

        rain = closest_row["precipitation"]

        valid = rain <= max_rain

        return {
            "valid": valid,
            "precipation": rain,
            "meta": {
                "rain": rain,
                "time": closest_row["time"],
                "matched_lat": closest_row["lat"],
                "matched_lon": closest_row["lon"]
            }
        }