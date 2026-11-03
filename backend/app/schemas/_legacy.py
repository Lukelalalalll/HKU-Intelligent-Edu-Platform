"""Shared request and response schemas for the pre-split API surface.

Every model here is re-exported by ``app.schemas`` and the domain modules,
so field names and validation rules are part of the public HTTP contract.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# User role literal shared by the auth and admin schemas.
Role = Literal["teacher", "student", "admin"]
# Semester literal matching the course check constraint.
CourseSemester = Literal["semester_1", "semester_2", "summer"]

class UserOut(BaseModel):
    """Public account fields returned by auth and profile endpoints."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    email: str
    name: str
    avatar_url: str | None
    role: Role

class RegisterIn(BaseModel):
    """Registration payload; the password is hashed before storage."""
    username: str = Field(min_length=3, max_length=80)
    email: str
    password: str = Field(min_length=6, max_length=128)
    name: str | None = Field(default=None, max_length=120)

class LoginIn(BaseModel):
    """Login payload accepting either username or email."""
    username: str
    password: str

class AuthResponse(BaseModel):
    """Auth result; the access token is only set for isolated sessions."""
    message: str
    user: UserOut
    # Development frontends use this short-lived access token in
    # sessionStorage so separate localhost tabs do not share cookies.
    access_token: str | None = None

class ProfileUpdateIn(BaseModel):
    """Partial profile update with email format validation."""
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

class PasswordChangeIn(BaseModel):
    """Password change payload carrying the current password."""
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)

class ScheduleIn(BaseModel):
    """Weekly schedule slot; weekday is ISO 1-7 and times are HH:MM."""
    weekday: int = Field(ge=1, le=7)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    room: str = ""
    timezone: str | None = None

class CourseCreate(BaseModel):
    """Course creation payload; the code is normalized on validation."""
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    academic_year_start: int = Field(ge=2000, le=2100)
    semester: CourseSemester
    timezone: str = "Asia/Hong_Kong"
    schedules: list[ScheduleIn] = Field(default_factory=list)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        """Upper-case the code and enforce the 4 letters + 4 digits shape."""
        normalized = value.strip()
        if not normalized.isascii() or len(normalized) != 8 or not normalized[:4].isalpha() or not normalized[4:].isdigit():
            raise ValueError("Course code must contain 4 letters followed by 4 digits")
        return normalized.upper()

class CourseOut(BaseModel):
    """Course summary with its schedules and enrolment count."""
    id: str
    code: str
    name: str
    description: str
    teacher_id: str
    academic_year_start: int
    semester: CourseSemester
    timezone: str = "Asia/Hong_Kong"
    teacher_name: str
    enrolled_count: int
    schedules: list[ScheduleIn]


class DiscussionAuthorOut(BaseModel):
    """Public author fields of a discussion comment."""
    id: str
    username: str
    name: str
    avatar_url: str | None


class DiscussionCommentCreate(BaseModel):
    """New comment payload, trimmed to non-empty text."""
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        """Trim the comment and reject an empty body."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Comment content cannot be empty")
        return normalized


class DiscussionCommentOut(BaseModel):
    """Comment tree node with like and reply counters."""
    id: str
    course_id: str
    parent_id: str | None
    author: DiscussionAuthorOut
    content: str
    created_at: datetime
    updated_at: datetime
    like_count: int
    liked_by_me: bool
    reply_count: int
    replies: list["DiscussionCommentOut"] = Field(default_factory=list)


class DiscussionLikeOut(BaseModel):
    """Result of liking or unliking a comment."""
    liked: bool
    like_count: int


# Material kind literal matching the chapter constraint.
MaterialKind = Literal["lecture", "tutorial"]


class CourseChapterCreate(BaseModel):
    """Chapter creation payload."""
    kind: MaterialKind
    title: str = Field(min_length=1, max_length=200)


class CourseChapterUpdate(BaseModel):
    """Partial chapter update: title and/or ordering."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    sort_order: int | None = Field(default=None, ge=0)


class CourseMaterialOut(BaseModel):
    """Material summary with its processing state."""
    id: str
    title: str
    file_name: str
    mime_type: str
    extension: str
    size_bytes: int
    uploaded_at: datetime
    download_url: str
    processing_status: str = "pending"
    processing_error: str | None = None
    document_id: str | None = None
    job_id: str | None = None
    processing_parser: str | None = None
    processing_fallback_reason: str | None = None


class CourseChapterOut(BaseModel):
    """Chapter with its materials."""
    id: str
    kind: MaterialKind
    title: str
    sort_order: int
    material_count: int
    materials: list[CourseMaterialOut]

class CoursewareQueryIn(BaseModel):
    """Courseware question plus optional course and attachments."""
    question: str = Field(min_length=1, max_length=20000)
    course_id: str | None = None
    conversation_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)

class CoursewareCitationOut(BaseModel):
    """Citation pointing at one material page."""
    course_id: str
    course_code: str
    course_name: str
    chapter_id: str
    chapter_title: str
    material_id: str
    material_title: str
    page_number: int | None = None
    href: str

class CoursewareQueryOut(BaseModel):
    """Grounded answer with citations and confidence."""
    course_id: str | None
    course: dict | None = None
    answer: str
    citations: list[CoursewareCitationOut] = Field(default_factory=list)
    confidence: float = 0.0
    needs_course_selection: bool = False
    candidate_courses: list[dict] = Field(default_factory=list)
    model: str | None = None

class ParticipantSummaryOut(BaseModel):
    """Student-facing participant summary."""
    id: str
    name: str
    email: str

class ParticipantDetailOut(ParticipantSummaryOut):
    """Teacher and admin participant detail."""
    username: str
    avatar_url: str | None
    enrolled_at: datetime

class AssignmentCreate(BaseModel):
    """Assignment creation payload with attached file assets."""
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    due_at: datetime | None = None
    max_score: int = Field(default=100, ge=1, le=1000)
    file_asset_ids: list[str] = Field(default_factory=list)

class AssignmentAttachmentOut(BaseModel):
    """Assignment attachment summary."""
    id: str
    file_asset_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    download_url: str

class AssignmentOut(BaseModel):
    """Assignment with its attachments."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    course_id: str
    title: str
    description: str
    due_at: datetime | None
    max_score: int
    status: str
    attachments: list[AssignmentAttachmentOut] = Field(default_factory=list)

class SubmissionCreate(BaseModel):
    """Submission payload; ids reference uploaded assets."""
    content: str = ""
    file_asset_id: str | None = None
    file_asset_ids: list[str] = Field(default_factory=list)

class SubmissionOut(BaseModel):
    """Submission with its attachment list."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    assignment_id: str
    student_id: str
    content: str
    file_asset_id: str | None
    submitted_at: datetime
    score: int | None
    feedback: str
    attachments: list[dict] = Field(default_factory=list)

class TeacherScheduleOut(ScheduleIn):
    """Teacher dashboard schedule row."""
    course_id: str
    course_code: str
    course_name: str

class PendingAssignmentOut(AssignmentOut):
    """Assignment with its ungraded submission count."""
    course_name: str
    pending_count: int

class TeacherDashboardOut(BaseModel):
    """Teacher dashboard payload."""
    courses: list[CourseOut]
    schedule: list[TeacherScheduleOut]
    pending_assignments: list[PendingAssignmentOut]


class StudentScheduleOut(ScheduleIn):
    """Student dashboard schedule row."""
    course_id: str
    course_code: str
    course_name: str
    teacher_name: str


class StudentAssignmentReminderOut(BaseModel):
    """Per-assignment reminder for the student dashboard.

    ``submission_status`` is ``not_started``, ``overdue``, ``submitted`` or
    ``graded``.
    """
    id: str
    course_id: str
    course_name: str
    title: str
    due_at: datetime | None
    max_score: int
    submission_status: Literal["not_started", "submitted", "graded", "overdue"]
    submitted_at: datetime | None
    score: int | None


class StudentDashboardOut(BaseModel):
    """Student dashboard payload."""
    timezone: str
    courses: list[CourseOut]
    schedule: list[StudentScheduleOut]
    assignment_reminders: list[StudentAssignmentReminderOut]


class LiveClassScheduleOut(BaseModel):
    """Live-class state for one schedule with windowed join flags."""
    meeting_id: str
    schedule_id: str
    weekday: int
    start_time: str
    end_time: str
    timezone: str
    status: str
    meeting_number: str
    next_start: datetime | None
    next_end: datetime | None
    can_join: bool
    can_start: bool


class LiveClassOut(BaseModel):
    """Live-class state of a course."""
    course_id: str
    course_name: str
    teacher_name: str
    timezone: str
    schedules: list[LiveClassScheduleOut]
    provisioning_required: bool
    status: str


class LiveClassAuthorizeIn(BaseModel):
    """Meeting SDK authorization request."""
    action: Literal["start", "join"]
    meeting_id: str | None = None


class LiveClassAuthorizeOut(BaseModel):
    """Signed Meeting SDK payload; the ZAK only goes to hosts."""
    meeting_number: str
    sdk_jwt: str
    sdk_key: str
    zak: str | None = None
    user_name: str
    role: int
    expires_at: datetime
    join_url: str


class LiveClassSessionOut(BaseModel):
    """Recording session of one occurrence."""
    id: str
    meeting_id: str
    status: str
    occurrence_start: datetime
    occurrence_end: datetime


class ZoomWebhookEvent(BaseModel):
    """Zoom webhook envelope."""
    event: str
    event_ts: int | None = None
    payload: dict = Field(default_factory=dict)

class AgentConversationOut(BaseModel):
    """Conversation summary."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    rag_mode: str
    created_at: datetime

class AgentMessageOut(BaseModel):
    """Stored message with its citations."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    conversation_id: str
    role: str
    content: str
    citations: list | dict
    model: str | None
    created_at: datetime

class AgentConversationDetail(AgentConversationOut):
    """Conversation with its messages."""
    messages: list[AgentMessageOut]

class AgentConversationCreate(BaseModel):
    """New conversation payload."""
    title: str = Field(default="新对话", min_length=1, max_length=200)
    course_id: str | None = None

class AgentMessageCreate(BaseModel):
    """New message payload with optional attachment ids."""
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)
    citations: list | dict = Field(default_factory=list)
    model: str | None = Field(default=None, max_length=100)
    attachment_ids: list[str] = Field(default_factory=list)

# Domain modules provide explicit stable imports without wildcard aggregation.
