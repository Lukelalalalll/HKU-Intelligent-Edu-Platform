"""Zoom Server-to-Server OAuth, recurring meetings and Meeting SDK tokens."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
import jwt

from app.core.config import settings
from app.models import Course, CourseSchedule
from app.services.course_terms import semester_date_range


class ZoomError(RuntimeError):
    """Failure from the Zoom API or configuration."""
    pass


class ZoomNotConfigured(ZoomError):
    """Raised when Zoom credentials are missing."""
    pass


@dataclass(frozen=True)
class Occurrence:
    """One scheduled class occurrence in the course timezone."""
    start: datetime
    end: datetime


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ZoomError(f"Invalid timezone: {name}") from exc


def _parse_hhmm(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":", 1))
    return time(hour, minute)


def next_occurrence(course: Course, schedule: CourseSchedule, now: datetime | None = None) -> Occurrence | None:
    """Return the next occurrence of a weekly schedule.

    Returns None once the next occurrence would fall past the semester end.
    """
    timezone_name = schedule.timezone or course.timezone or settings.zoom_default_timezone
    tz = _zone(timezone_name)
    local_now = (now or datetime.now(timezone.utc)).astimezone(tz)
    term_start, term_end = semester_date_range(course.academic_year_start, course.semester)
    candidate_date = max(local_now.date(), term_start)
    days_ahead = (schedule.weekday - candidate_date.isoweekday()) % 7
    candidate_date += timedelta(days=days_ahead)
    start = datetime.combine(candidate_date, _parse_hhmm(schedule.start_time), tz)
    end = datetime.combine(candidate_date, _parse_hhmm(schedule.end_time), tz)
    if end <= start:
        end += timedelta(days=1)
    if start < local_now and local_now > end + timedelta(minutes=30):
        candidate_date += timedelta(days=7)
        start = datetime.combine(candidate_date, _parse_hhmm(schedule.start_time), tz)
        end = datetime.combine(candidate_date, _parse_hhmm(schedule.end_time), tz)
        if end <= start:
            end += timedelta(days=1)
    if start.date() > term_end:
        return None
    return Occurrence(start=start, end=end)


def within_window(occurrence: Occurrence | None, now: datetime | None = None) -> tuple[bool, bool]:
    """Report ``(join_window, start_window)`` for an occurrence.

    Joining opens 15 minutes early and closes 30 minutes after the end;
    starting closes at the scheduled end.
    """
    if not occurrence:
        return False, False
    current = now or datetime.now(timezone.utc)
    start = occurrence.start.astimezone(timezone.utc)
    end = occurrence.end.astimezone(timezone.utc)
    return start - timedelta(minutes=15) <= current <= end + timedelta(minutes=30), start - timedelta(minutes=15) <= current <= end


class ZoomClient:
    """Cached-token client for the Zoom REST API."""
    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._lock = Lock()

    @property
    def configured(self) -> bool:
        """Return whether the server-to-server credentials are set."""
        return bool(settings.zoom_account_id and settings.zoom_client_id and settings.zoom_client_secret)

    def _ensure_configured(self) -> None:
        if not self.configured:
            raise ZoomNotConfigured("Zoom integration is not configured")

    def access_token(self) -> str:
        """Return a cached access token, refreshing it when expired.

        Raises:
            ZoomNotConfigured: when credentials are missing.
            ZoomError: when the OAuth exchange fails.
        """
        self._ensure_configured()
        now = datetime.now(timezone.utc)
        with self._lock:
            if self._token and self._token_expires_at and now < self._token_expires_at:
                return self._token
            raw = f"{settings.zoom_client_id}:{settings.zoom_client_secret}".encode()
            basic = base64.b64encode(raw).decode()
            response = httpx.post(
                "https://zoom.us/oauth/token",
                params={"grant_type": "account_credentials", "account_id": settings.zoom_account_id},
                headers={"Authorization": f"Basic {basic}"},
                timeout=15,
            )
            if response.status_code >= 400:
                raise ZoomError(f"Zoom OAuth failed ({response.status_code})")
            payload = response.json()
            self._token = payload["access_token"]
            self._token_expires_at = now + timedelta(seconds=max(60, int(payload.get("expires_in", 3600)) - 60))
            return self._token

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Call the Zoom API with retries for 429 and 5xx responses.

        Raises:
            ZoomError: when every attempt fails or the API returns an error.
        """
        token = self.access_token()
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {token}"
        url = f"{settings.zoom_api_base_url.rstrip('/')}/{path.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = httpx.request(method, url, headers=headers, timeout=20, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        continue
                if response.status_code >= 400:
                    raise ZoomError(f"Zoom API error ({response.status_code})")
                return response.json() if response.content else {}
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt == 2:
                    break
        raise ZoomError("Zoom API request failed") from last_error

    def create_recurring_meeting(self, *, topic: str, occurrence: Occurrence, weekday: int, timezone_name: str, recurrence_end: date) -> dict[str, Any]:
        """Create a weekly recurring meeting for one schedule."""
        payload = {
            "topic": topic[:200],
            "type": 8,
            "start_time": occurrence.start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "duration": max(1, int((occurrence.end - occurrence.start).total_seconds() // 60)),
            "timezone": timezone_name,
            "recurrence": {"type": 2, "repeat_interval": 1, "weekly_days": str(weekday), "end_date_time": datetime.combine(recurrence_end, time.max, occurrence.end.tzinfo).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")},
            "settings": {"waiting_room": True, "join_before_host": False, "mute_upon_entry": True, "participant_video": False},
        }
        return self.request("POST", f"users/{settings.zoom_host_user_id}/meetings", json=payload)

    def update_meeting(self, meeting_id: str, *, topic: str, occurrence: Occurrence, weekday: int, timezone_name: str) -> dict[str, Any]:
        """Update topic, time, duration and recurrence of a meeting."""
        payload = {
            "topic": topic[:200],
            "start_time": occurrence.start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "duration": max(1, int((occurrence.end - occurrence.start).total_seconds() // 60)),
            "timezone": timezone_name,
            "recurrence": {"type": 2, "repeat_interval": 1, "weekly_days": str(weekday)},
        }
        return self.request("PATCH", f"meetings/{meeting_id}", json=payload)

    def get_zak(self) -> str:
        """Return the host's Zoom Access Key for starting a meeting."""
        payload = self.request("GET", f"users/{settings.zoom_host_user_id}/token", params={"type": "zak"})
        return str(payload["token"])


@lru_cache(maxsize=1)
def get_zoom_client() -> ZoomClient:
    """Return the process-wide Zoom client."""
    return ZoomClient()


def meeting_sdk_jwt(meeting_number: str, role: int) -> tuple[str, datetime]:
    """Sign a Meeting SDK JWT for one meeting and role.

    Role 1 is host and 0 is participant; the token expires one hour after
    issue.

    Raises:
        ZoomNotConfigured: when Meeting SDK credentials are missing.
    """
    sdk_key = settings.zoom_sdk_client_id or settings.zoom_sdk_key
    if not sdk_key or not settings.zoom_sdk_secret:
        raise ZoomNotConfigured("Meeting SDK credentials are not configured")
    now = datetime.now(timezone.utc)
    issued = int(now.timestamp()) - 30
    expires = issued + 60 * 60
    token = jwt.encode(
        {"appKey": sdk_key, "mn": str(meeting_number), "role": role, "iat": issued, "exp": expires, "tokenExp": expires},
        settings.zoom_sdk_secret,
        algorithm="HS256",
    )
    return token, datetime.fromtimestamp(expires, timezone.utc)
