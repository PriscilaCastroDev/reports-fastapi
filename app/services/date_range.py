from datetime import datetime, timedelta


def get_date_range(granularity: str, value: dict) -> tuple[datetime, datetime]:
    """
    Returns (from, to) based on granularity. `to` is exclusive (use < in SQL).
    """
    if granularity == "DAY":
        day = datetime.strptime(value["date"], "%Y-%m-%d")
        return day, day + timedelta(days=1)

    if granularity == "WEEK":
        year = int(value["year"])
        month = int(value["month"])
        week = int(value["week"])
        first_of_month = datetime(year, month, 1)
        # Monday on or before the 1st of the month
        days_since_monday = first_of_month.weekday()
        first_monday = first_of_month - timedelta(days=days_since_monday)
        week_start = first_monday + timedelta(weeks=week - 1)
        return week_start, week_start + timedelta(days=7)

    if granularity == "MONTH":
        year, month = map(int, value["month"].split("-"))
        start = datetime(year, month, 1)
        next_month = datetime(year + (month // 12), (month % 12) + 1, 1)
        return start, next_month

    raise ValueError(f"Granularidad inválida: {granularity}")


def get_period_label(granularity: str, value: dict) -> str:
    if granularity == "DAY":
        return value["date"]
    if granularity == "WEEK":
        return f"{value['year']}-{int(value['month']):02d}-w{value['week']}"
    if granularity == "MONTH":
        return value["month"]
    raise ValueError(f"Granularidad inválida: {granularity}")
