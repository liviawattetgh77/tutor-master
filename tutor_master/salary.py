import datetime as dt
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable

from .scheduling import Course, HOLIDAY_MONTHS, grade_sort_key

BASE_SALARY = 5000
HOLIDAY_DUTY = 10
REGULAR_DUTY = 5

HOURLY_RATE: Dict[str, int] = {
    "初一": 130,
    "初二": 140,
    "初三": 150,
    "高一": 180,
    "高二": 190,
    "高三": 200,
}


@dataclass
class SalaryBreakdown:
    month_name: str
    payable_hours: float
    duty_hours: float
    hourly_income: float
    renew_bonus: float
    class_bonus: float
    penalty: float
    total: float


@dataclass
class DutyResult:
    total_hours: float
    payable_hours: float


def _subtract_duty(hours_by_grade: Dict[str, float], is_holiday: bool) -> DutyResult:
    duty = HOLIDAY_DUTY if is_holiday else REGULAR_DUTY
    sorted_grades = sorted(hours_by_grade.keys(), key=grade_sort_key)
    remaining = duty
    for grade in sorted_grades:
        if remaining <= 0:
            break
        available = hours_by_grade[grade]
        deduction = min(available, remaining)
        hours_by_grade[grade] -= deduction
        remaining -= deduction
    total_hours = sum(hours_by_grade.values())
    return DutyResult(total_hours=total_hours, payable_hours=duty - remaining)


def calculate_hours(courses: Iterable[Course], is_holiday: bool) -> DutyResult:
    hours_by_grade: Dict[str, float] = defaultdict(float)
    for course in courses:
        hours_by_grade[course.grade_level] += course.course_hours
    return _subtract_duty(hours_by_grade, is_holiday)


def calculate_salary(
    courses: Iterable[Course],
    month_name: str,
    *,
    renew_bonus: float = 0,
    class_bonus: float = 0,
    penalty: float = 0,
    is_holiday: bool = False,
) -> SalaryBreakdown:
    duty_result = calculate_hours(courses, is_holiday)
    hourly_income = 0.0
    for course in courses:
        hourly_income += course.course_hours * HOURLY_RATE.get(course.grade_level, 0)
    hourly_income = round(hourly_income, 2)
    total = BASE_SALARY + hourly_income + renew_bonus + class_bonus - penalty
    return SalaryBreakdown(
        month_name=month_name,
        payable_hours=duty_result.total_hours,
        duty_hours=duty_result.payable_hours,
        hourly_income=hourly_income,
        renew_bonus=renew_bonus,
        class_bonus=class_bonus,
        penalty=penalty,
        total=round(total, 2),
    )


def filter_courses_for_month(courses: Iterable[Course], start: dt.date, end: dt.date):
    for course in courses:
        if start <= course.course_date <= end:
            yield course
