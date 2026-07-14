# utils for datetime functions

from datetime import datetime, date, timedelta
import pandas as pd

from utils.geometry import reachable


def validate_date_range(date_str: str):
    # parse input
    d = datetime.strptime(date_str, "%Y-%m-%d").date()

    today = date.today()

    lower_bound = today - timedelta(days=90)
    upper_bound = today + timedelta(weeks=2)

    # check range (inclusive)
    if not (lower_bound <= d <= upper_bound):
        raise ValueError(
            f"Date {date_str} not in allowed range "
            f"{lower_bound} to {upper_bound}"
        )

    return True


def evaluate_departure_times(
        weather_df,
        start,
        start_time,
        hours,
        avg_speed=80
):
    """
    Evaluate all possible departure times in a timeframe.

    Returns:
        dataframe with:
        departure_time
        total_precipitation
        reachable_points
    """

    results = []

    current_time = start_time

    for _ in range(hours):

        reachable_df = reachable(
            df=weather_df.copy(),
            start=start,
            departure_time=current_time,
            avg_speed=avg_speed,
        )

        total_precipitation = (
            reachable_df["precipitation"]
            .sum()
        )

        results.append(
            {
                "departure_time": current_time,
                "total_precipitation": total_precipitation,
                "reachable_points": len(reachable_df)
            }
        )

        current_time += pd.Timedelta(hours=1)

    return pd.DataFrame(results)