from datetime import datetime, timezone

import jwt

from app.models import Course, CourseSchedule
from app.services.zoom import next_occurrence, within_window
import app.services.zoom as zoom


def test_next_occurrence_uses_course_term_and_timezone(monkeypatch):
    course = Course(academic_year_start=2025, semester="semester_1", timezone="Asia/Hong_Kong", code="COMP2119", name="Test", teacher_id="t")
    schedule = CourseSchedule(weekday=2, start_time="10:00", end_time="12:00", timezone=None)
    now = datetime(2025, 9, 1, 1, 0, tzinfo=timezone.utc)
    occurrence = next_occurrence(course, schedule, now)
    assert occurrence is not None
    assert occurrence.start.isoformat().startswith("2025-09-02T10:00:00+08:00")
    assert (occurrence.end - occurrence.start).total_seconds() == 7200
    in_progress = next_occurrence(course, schedule, datetime(2025, 9, 2, 3, 30, tzinfo=timezone.utc))
    assert in_progress is not None and in_progress.start.date().isoformat() == "2025-09-02"


def test_within_window_has_early_join_and_post_class_grace():
    course = Course(academic_year_start=2025, semester="semester_1", timezone="Asia/Hong_Kong", code="COMP2119", name="Test", teacher_id="t")
    schedule = CourseSchedule(weekday=2, start_time="10:00", end_time="12:00")
    occurrence = next_occurrence(course, schedule, datetime(2025, 9, 1, 1, 0, tzinfo=timezone.utc))
    assert occurrence is not None
    assert within_window(occurrence, occurrence.start.astimezone(timezone.utc)) == (True, True)
    assert within_window(occurrence, occurrence.end.astimezone(timezone.utc).replace(hour=4, minute=15)) == (True, False)


def test_meeting_sdk_jwt_contains_required_claims(monkeypatch):
    monkeypatch.setattr(zoom.settings, "zoom_sdk_client_id", "sdk-key")
    monkeypatch.setattr(zoom.settings, "zoom_sdk_secret", "sdk-secret")
    token, expires = zoom.meeting_sdk_jwt("123456789", 1)
    payload = jwt.decode(token, "sdk-secret", algorithms=["HS256"])
    assert payload["appKey"] == "sdk-key"
    assert payload["mn"] == "123456789"
    assert payload["role"] == 1
    assert payload["tokenExp"] == payload["exp"]
    assert expires > datetime.now(timezone.utc)
