from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models import Course, CourseSchedule, CourseZoomMeeting, Enrollment, RecordingSession, User, UserRole
from app.schemas import LiveClassAuthorizeIn, LiveClassAuthorizeOut, LiveClassOut, LiveClassScheduleOut, LiveClassSessionOut, ZoomWebhookEvent
from app.services.course_terms import semester_date_range
from app.services.zoom import ZoomError, ZoomNotConfigured, get_zoom_client, meeting_sdk_jwt, next_occurrence, within_window

router = APIRouter(prefix="/api/courses/{course_id}/live-class", tags=["live-class"])
webhook_router = APIRouter(prefix="/api/zoom", tags=["zoom"])


def _course(course_id: str, user: User, db: Session) -> Course:
    course = db.scalar(select(Course).options(selectinload(Course.schedules), selectinload(Course.zoom_meetings)).where(Course.id == course_id))
    if not course:
        raise HTTPException(404, "Course not found")
    if user.role == UserRole.teacher and course.teacher_id != user.id:
        raise HTTPException(403, "Course access denied")
    if user.role == UserRole.student and not db.scalar(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == user.id)):
        raise HTTPException(403, "You are not enrolled in this course")
    return course


def _meeting_map(course: Course) -> dict[str, CourseZoomMeeting]:
    return {meeting.schedule_id: meeting for meeting in course.zoom_meetings}


@router.get("", response_model=LiveClassOut)
def get_live_class(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course(course_id, user, db)
    meetings = _meeting_map(course)
    client = get_zoom_client()
    schedules: list[LiveClassScheduleOut] = []
    for schedule in course.schedules:
        meeting = meetings.get(schedule.id)
        occurrence = next_occurrence(course, schedule)
        join_window, start_window = within_window(occurrence)
        schedules.append(LiveClassScheduleOut(
            meeting_id=meeting.id if meeting else "",
            schedule_id=schedule.id,
            weekday=schedule.weekday,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            timezone=schedule.timezone or course.timezone or settings.zoom_default_timezone,
            status=meeting.status if meeting else ("unconfigured" if not client.configured else "provisioning_required"),
            meeting_number=meeting.zoom_meeting_id if meeting else "",
            next_start=occurrence.start if occurrence else None,
            next_end=occurrence.end if occurrence else None,
            can_join=bool(meeting and join_window),
            can_start=bool(meeting and start_window and user.role in (UserRole.teacher, UserRole.admin)),
        ))
    active = [item for item in schedules if item.can_join]
    return LiveClassOut(course_id=course.id, course_name=course.name, teacher_name=course.teacher.name, timezone=course.timezone, schedules=schedules, provisioning_required=not client.configured or any(not item.meeting_id for item in schedules), status="open" if active else "scheduled")


@router.post("/provision", response_model=LiveClassOut)
def provision_live_class(course_id: str, user: User = Depends(require_roles(UserRole.teacher, UserRole.admin)), db: Session = Depends(get_db)):
    course = _course(course_id, user, db)
    client = get_zoom_client()
    try:
        meetings = _meeting_map(course)
        for schedule in course.schedules:
            occurrence = next_occurrence(course, schedule)
            if not occurrence:
                continue
            timezone_name = schedule.timezone or course.timezone or settings.zoom_default_timezone
            topic = f"{course.code} · {course.name}"
            meeting = meetings.get(schedule.id)
            if meeting:
                client.update_meeting(meeting.zoom_meeting_id, topic=topic, occurrence=occurrence, weekday=schedule.weekday, timezone_name=timezone_name)
                meeting.topic = topic
                meeting.duration_minutes = max(1, int((occurrence.end - occurrence.start).total_seconds() // 60))
                meeting.timezone = timezone_name
                meeting.last_synced_at = datetime.now(timezone.utc)
            else:
                _, term_end = semester_date_range(course.academic_year_start, course.semester)
                payload = client.create_recurring_meeting(topic=topic, occurrence=occurrence, weekday=schedule.weekday, timezone_name=timezone_name, recurrence_end=term_end)
                meeting = CourseZoomMeeting(course_id=course.id, schedule_id=schedule.id, zoom_meeting_id=str(payload["id"]), topic=topic, timezone=timezone_name, duration_minutes=max(1, int((occurrence.end - occurrence.start).total_seconds() // 60)), join_url=str(payload.get("join_url", "")), last_synced_at=datetime.now(timezone.utc))
                db.add(meeting)
        db.commit()
    except ZoomNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except ZoomError as exc:
        db.rollback()
        raise HTTPException(502, str(exc)) from exc
    return get_live_class(course_id, user, db)


@router.post("/session", response_model=LiveClassSessionOut)
def create_session(course_id: str, payload: LiveClassAuthorizeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course(course_id, user, db)
    meeting = db.scalar(select(CourseZoomMeeting).where(CourseZoomMeeting.course_id == course_id, CourseZoomMeeting.id == payload.meeting_id)) if payload.meeting_id else db.scalar(select(CourseZoomMeeting).where(CourseZoomMeeting.course_id == course_id).order_by(CourseZoomMeeting.id))
    if not meeting:
        raise HTTPException(404, "Live class meeting is not provisioned")
    schedule = db.get(CourseSchedule, meeting.schedule_id)
    occurrence = next_occurrence(course, schedule)
    join_window, _ = within_window(occurrence)
    if not occurrence or not join_window:
        raise HTTPException(409, "The class is outside its join window")
    existing = db.scalar(select(RecordingSession).where(RecordingSession.course_id == course_id, RecordingSession.zoom_meeting_fk == meeting.id, RecordingSession.occurrence_start == occurrence.start))
    if not existing:
        existing = RecordingSession(course_id=course_id, zoom_meeting_id=meeting.zoom_meeting_id, zoom_meeting_fk=meeting.id, schedule_id=schedule.id, occurrence_start=occurrence.start, occurrence_end=occurrence.end, status="planned")
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return LiveClassSessionOut(id=existing.id, meeting_id=meeting.id, status=existing.status, occurrence_start=occurrence.start, occurrence_end=occurrence.end)


@router.post("/authorize", response_model=LiveClassAuthorizeOut)
def authorize_live_class(course_id: str, payload: LiveClassAuthorizeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = _course(course_id, user, db)
    meeting = db.scalar(select(CourseZoomMeeting).where(CourseZoomMeeting.course_id == course_id, CourseZoomMeeting.id == payload.meeting_id)) if payload.meeting_id else db.scalar(select(CourseZoomMeeting).where(CourseZoomMeeting.course_id == course_id).order_by(CourseZoomMeeting.id))
    if not meeting:
        raise HTTPException(404, "Live class meeting is not provisioned")
    schedule = db.get(CourseSchedule, meeting.schedule_id)
    occurrence = next_occurrence(course, schedule)
    join_window, start_window = within_window(occurrence)
    if not occurrence or not join_window:
        raise HTTPException(409, "The class is outside its join window")
    if payload.action == "start" and user.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(403, "Only the course teacher can start the class")
    if payload.action == "start" and not start_window:
        raise HTTPException(409, "The class cannot be started at this time")
    try:
        role = 1 if payload.action == "start" else 0
        sdk_token, expires_at = meeting_sdk_jwt(meeting.zoom_meeting_id, role)
        zak = get_zoom_client().get_zak() if role == 1 else None
    except ZoomNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    session = db.scalar(select(RecordingSession).where(RecordingSession.course_id == course_id, RecordingSession.zoom_meeting_fk == meeting.id, RecordingSession.occurrence_start == occurrence.start))
    if not session:
        session = RecordingSession(course_id=course_id, zoom_meeting_id=meeting.zoom_meeting_id, zoom_meeting_fk=meeting.id, schedule_id=schedule.id, occurrence_start=occurrence.start, occurrence_end=occurrence.end, status="live" if role == 1 else "planned", started_at=datetime.now(timezone.utc) if role == 1 else None)
        db.add(session)
    elif role == 1 and session.status == "planned":
        session.status = "live"
        session.started_at = datetime.now(timezone.utc)
    db.commit()
    return LiveClassAuthorizeOut(meeting_number=meeting.zoom_meeting_id, sdk_jwt=sdk_token, sdk_key=settings.zoom_sdk_client_id or settings.zoom_sdk_key, zak=zak, user_name=user.name, role=role, expires_at=expires_at, join_url=meeting.join_url)


@webhook_router.post("/webhooks")
async def zoom_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    timestamp = request.headers.get("x-zm-request-timestamp", "")
    signature = request.headers.get("x-zm-signature", "")
    if settings.zoom_webhook_secret_token:
        message = f"v0:{timestamp}:{body.decode()}".encode()
        expected = "v0=" + hmac.new(settings.zoom_webhook_secret_token.encode(), message, hashlib.sha256).hexdigest()
        if not timestamp or not hmac.compare_digest(expected, signature):
            raise HTTPException(401, "Invalid Zoom webhook signature")
    try:
        event = ZoomWebhookEvent.model_validate(json.loads(body))
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, "Invalid webhook payload") from exc
    if event.event == "endpoint.url_validation":
        plain = event.payload.get("plainToken", "")
        encrypted = hmac.new(settings.zoom_webhook_secret_token.encode(), plain.encode(), hashlib.sha256).hexdigest()
        return {"plainToken": plain, "encryptedToken": encrypted}
    event_id = str(event.payload.get("object", {}).get("id", "")) + ":" + event.event + ":" + str(event.event_ts or "")
    if not event_id.strip(":"):
        return {"ok": True}
    meeting_number = str(event.payload.get("object", {}).get("id", ""))
    session = db.scalar(select(RecordingSession).where(RecordingSession.zoom_meeting_id == meeting_number).order_by(RecordingSession.occurrence_start.desc()))
    if session and session.last_webhook_event_id != event_id:
        session.last_webhook_event_id = event_id
        if event.event == "meeting.started":
            session.status = "live"
            session.started_at = session.started_at or datetime.now(timezone.utc)
        elif event.event == "meeting.ended":
            session.status = "ended"
            session.ended_at = datetime.now(timezone.utc)
        db.commit()
    return {"ok": True}
