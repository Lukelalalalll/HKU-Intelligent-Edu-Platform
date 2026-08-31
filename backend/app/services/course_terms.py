from __future__ import annotations

from datetime import date, datetime
from typing import Literal

CourseSemester = Literal["semester_1", "semester_2", "summer"]
COURSE_SEMESTERS: tuple[CourseSemester, ...] = ("semester_1", "semester_2", "summer")


def academic_year_start_for(value: date | datetime) -> int:
    month = value.month
    year = value.year
    return year if month >= 9 else year - 1


def semester_for(value: date | datetime) -> CourseSemester:
    month = value.month
    if 9 <= month <= 12:
        return "semester_1"
    if 2 <= month <= 5:
        return "semester_2"
    if 6 <= month <= 8:
        return "summer"
    # January is the inter-semester break; preselect the upcoming semester.
    return "semester_2"


def semester_date_range(academic_year_start: int, semester: CourseSemester) -> tuple[date, date]:
    following_year = academic_year_start + 1
    ranges: dict[CourseSemester, tuple[date, date]] = {
        "semester_1": (date(academic_year_start, 9, 1), date(academic_year_start, 12, 31)),
        "semester_2": (date(following_year, 2, 1), date(following_year, 5, 31)),
        "summer": (date(following_year, 6, 1), date(following_year, 8, 31)),
    }
    return ranges[semester]

