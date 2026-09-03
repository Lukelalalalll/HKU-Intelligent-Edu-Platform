from datetime import date

import pytest

from app.schemas import CourseCreate
from app.services.course_terms import academic_year_start_for, semester_date_range, semester_for


def test_three_semester_boundaries():
    assert semester_for(date(2026, 9, 1)) == "semester_1"
    assert semester_for(date(2026, 12, 31)) == "semester_1"
    assert semester_for(date(2027, 1, 1)) == "semester_2"
    assert semester_for(date(2027, 2, 1)) == "semester_2"
    assert semester_for(date(2027, 5, 31)) == "semester_2"
    assert semester_for(date(2027, 6, 1)) == "summer"
    assert semester_for(date(2027, 8, 31)) == "summer"


def test_academic_year_and_ranges():
    assert academic_year_start_for(date(2026, 9, 1)) == 2026
    assert academic_year_start_for(date(2027, 1, 1)) == 2026
    assert semester_date_range(2026, "semester_2") == (date(2027, 2, 1), date(2027, 5, 31))
    assert semester_date_range(2026, "summer") == (date(2027, 6, 1), date(2027, 8, 31))


def test_course_payload_requires_a_valid_semester():
    with pytest.raises(ValueError):
        CourseCreate(code="HKU-101", name="Demo", academic_year_start=2026, semester="winter")


def test_course_code_is_normalized_to_uppercase():
    payload = CourseCreate(code=" comp2119 ", name="Demo", academic_year_start=2026, semester="semester_1")
    assert payload.code == "COMP2119"


@pytest.mark.parametrize("code", ["ABC1234", "COMP-2119", "COMP211", "COMP21A9", "中文2119"])
def test_course_code_requires_four_letters_and_four_digits(code):
    with pytest.raises(ValueError):
        CourseCreate(code=code, name="Demo", academic_year_start=2026, semester="semester_1")
