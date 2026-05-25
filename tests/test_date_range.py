import pytest
from datetime import datetime

from app.services.date_range import get_date_range, get_period_label


class TestDay:
    def test_basic(self) -> None:
        frm, to = get_date_range("DAY", {"date": "2026-05-21"})
        assert frm == datetime(2026, 5, 21, 0, 0, 0)
        assert to == datetime(2026, 5, 22, 0, 0, 0)

    def test_last_day_of_month(self) -> None:
        frm, to = get_date_range("DAY", {"date": "2026-05-31"})
        assert to == datetime(2026, 6, 1, 0, 0, 0)

    def test_span_is_exactly_one_day(self) -> None:
        frm, to = get_date_range("DAY", {"date": "2026-03-10"})
        assert (to - frm).days == 1


class TestMonth:
    def test_basic(self) -> None:
        frm, to = get_date_range("MONTH", {"month": "2026-05"})
        assert frm == datetime(2026, 5, 1)
        assert to == datetime(2026, 6, 1)

    def test_december_wraps_year(self) -> None:
        frm, to = get_date_range("MONTH", {"month": "2026-12"})
        assert frm == datetime(2026, 12, 1)
        assert to == datetime(2027, 1, 1)

    def test_february(self) -> None:
        frm, to = get_date_range("MONTH", {"month": "2026-02"})
        assert frm == datetime(2026, 2, 1)
        assert to == datetime(2026, 3, 1)


class TestWeek:
    def test_week3_may_2026(self) -> None:
        # May 1 2026 is Friday (weekday=4)
        # first_monday = April 27
        # week 1: Apr 27–May 3, week 2: May 4–10, week 3: May 11–17
        frm, to = get_date_range("WEEK", {"year": 2026, "month": 5, "week": 3})
        assert frm == datetime(2026, 5, 11)
        assert to == datetime(2026, 5, 18)

    def test_week1_starts_on_monday(self) -> None:
        frm, _ = get_date_range("WEEK", {"year": 2026, "month": 5, "week": 1})
        assert frm.weekday() == 0  # Monday

    def test_span_is_7_days(self) -> None:
        frm, to = get_date_range("WEEK", {"year": 2026, "month": 5, "week": 2})
        assert (to - frm).days == 7

    def test_month_starting_on_monday(self) -> None:
        # June 1 2026 is Monday (weekday=0), so first_monday = June 1 itself
        frm, _ = get_date_range("WEEK", {"year": 2026, "month": 6, "week": 1})
        assert frm == datetime(2026, 6, 1)


class TestInvalidGranularity:
    def test_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Granularidad inválida"):
            get_date_range("QUARTER", {"date": "2026-05-21"})


class TestPeriodLabel:
    def test_day(self) -> None:
        assert get_period_label("DAY", {"date": "2026-05-21"}) == "2026-05-21"

    def test_month(self) -> None:
        assert get_period_label("MONTH", {"month": "2026-05"}) == "2026-05"

    def test_week(self) -> None:
        label = get_period_label("WEEK", {"year": 2026, "month": 5, "week": 3})
        assert label == "2026-05-w3"

    def test_week_zero_pads_month(self) -> None:
        label = get_period_label("WEEK", {"year": 2026, "month": 1, "week": 2})
        assert label == "2026-01-w2"
