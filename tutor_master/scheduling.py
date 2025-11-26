import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .database import GRADE_LEVELS


DEFAULT_SLOTS = [
    (dt.time(8, 0), dt.time(10, 0)),
    (dt.time(10, 20), dt.time(12, 0)),
    (dt.time(13, 0), dt.time(15, 0)),
    (dt.time(15, 20), dt.time(17, 0)),
    (dt.time(19, 0), dt.time(21, 0)),
]

# Color mapping: mid school yellow series, high school blue series
GRADE_COLORS: Dict[str, str] = {
    "初一": "#fff4b3",
    "初二": "#ffe066",
    "初三": "#ffd43b",
    "高一": "#cce0ff",
    "高二": "#99c2ff",
    "高三": "#6690ff",
}


@dataclass
class Course:
    id: int
    title: str
    course_date: dt.date
    start_time: dt.time
    end_time: dt.time
    course_type: str
    grade_level: str
    is_trial: bool
    students: List[str]
    notes: str = ""
    location: str = ""
    subject: str = ""

    @property
    def duration_hours(self) -> float:
        start_dt = dt.datetime.combine(self.course_date, self.start_time)
        end_dt = dt.datetime.combine(self.course_date, self.end_time)
        return round((end_dt - start_dt).total_seconds() / 3600, 2)

    @property
    def course_hours(self) -> float:
        # each 2h is one class hour unless custom
        return self.duration_hours / 2


HOLIDAY_MONTHS = {2, 7, 8}


@dataclass
class CourseMonth:
    month_name: str
    start_date: dt.date
    end_date: dt.date
    is_holiday: bool
    quarter: int


def find_course_month(anchor: dt.date) -> CourseMonth:
    # course month covers Monday->Sunday around calendar month
    first_of_month = anchor.replace(day=1)
    last_day = (first_of_month.replace(month=anchor.month % 12 + 1, day=1) - dt.timedelta(days=1)).day
    last_of_month = anchor.replace(day=last_day)
    start_candidate = first_of_month - dt.timedelta(days=(first_of_month.weekday()))
    if (first_of_month - start_candidate).days > 3:
        start_candidate += dt.timedelta(days=7)
    end_candidate = start_candidate + dt.timedelta(days=34)
    while end_candidate.month == anchor.month and end_candidate.day < last_day:
        end_candidate += dt.timedelta(days=7)
    # align to Sunday
    end_candidate = end_candidate + dt.timedelta(days=(6 - end_candidate.weekday()))
    if (end_candidate - last_of_month).days > 3:
        end_candidate -= dt.timedelta(days=7)

    quarter = ((anchor.month + 2) % 12) // 3 + 1
    is_holiday = anchor.month in HOLIDAY_MONTHS
    return CourseMonth(
        month_name=f"{anchor.year}年{anchor.month:02d}月",
        start_date=start_candidate,
        end_date=end_candidate,
        is_holiday=is_holiday,
        quarter=quarter,
    )


def group_by_week(start_date: dt.date, end_date: dt.date) -> List[Tuple[dt.date, dt.date]]:
    weeks: List[Tuple[dt.date, dt.date]] = []
    cursor = start_date
    while cursor <= end_date:
        week_start = cursor
        week_end = cursor + dt.timedelta(days=6)
        weeks.append((week_start, week_end))
        cursor = week_end + dt.timedelta(days=1)
    return weeks


def grade_sort_key(grade: str) -> int:
    return GRADE_LEVELS.index(grade) if grade in GRADE_LEVELS else len(GRADE_LEVELS)
