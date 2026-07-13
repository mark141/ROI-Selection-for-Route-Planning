# utils for datetime functions

from datetime import datetime, date, timedelta


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