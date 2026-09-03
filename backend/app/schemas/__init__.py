from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["teacher", "student", "admin"]
CourseSemester = Literal["semester_1", "semester_2", "summer"]

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    email: str
    name: str
    avatar_url: str | None
    role: Role

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: str
    password: str = Field(min_length=6, max_length=128)
    name: str | None = Field(default=None, max_length=120)

class LoginIn(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    message: str
    user: UserOut
    # Development frontends use this short-lived access token in
    # sessionStorage so separate localhost tabs do not share cookies.
    access_token: str | None = None

class ProfileUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)

class ScheduleIn(BaseModel):
    weekday: int = Field(ge=1, le=7)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    room: str = ""
    timezone: str | None = None

class CourseCreate(BaseModel):
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
        normalized = value.strip()
        if not normalized.isascii() or len(normalized) != 8 or not normalized[:4].isalpha() or not normalized[4:].isdigit():
            raise ValueError("Course code must contain 4 letters followed by 4 digits")
        return normalized.upper()

class CourseOut(BaseModel):
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

class AssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    due_at: datetime | None = None
    max_score: int = Field(default=100, ge=1, le=1000)

class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    course_id: str
    title: str
    description: str
    due_at: datetime | None
    max_score: int
    status: str

class SubmissionCreate(BaseModel):
    content: str = ""
    file_asset_id: str | None = None

class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    assignment_id: str
    student_id: str
    content: str
    file_asset_id: str | None
    submitted_at: datetime
    score: int | None
    feedback: str

class TeacherScheduleOut(ScheduleIn):
    course_id: str
    course_code: str
    course_name: str

class PendingAssignmentOut(AssignmentOut):
    course_name: str
    pending_count: int

class TeacherDashboardOut(BaseModel):
    courses: list[CourseOut]
    schedule: list[TeacherScheduleOut]
    pending_assignments: list[PendingAssignmentOut]


class LiveClassScheduleOut(BaseModel):
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
    course_id: str
    course_name: str
    teacher_name: str
    timezone: str
    schedules: list[LiveClassScheduleOut]
    provisioning_required: bool
    status: str


class LiveClassAuthorizeIn(BaseModel):
    action: Literal["start", "join"]
    meeting_id: str | None = None


class LiveClassAuthorizeOut(BaseModel):
    meeting_number: str
    sdk_jwt: str
    sdk_key: str
    zak: str | None = None
    user_name: str
    role: int
    expires_at: datetime
    join_url: str


class LiveClassSessionOut(BaseModel):
    id: str
    meeting_id: str
    status: str
    occurrence_start: datetime
    occurrence_end: datetime


class ZoomWebhookEvent(BaseModel):
    event: str
    event_ts: int | None = None
    payload: dict = Field(default_factory=dict)

class AgentConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    rag_mode: str
    created_at: datetime

class AgentMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    conversation_id: str
    role: str
    content: str
    citations: list | dict
    model: str | None
    created_at: datetime

class AgentConversationDetail(AgentConversationOut):
    messages: list[AgentMessageOut]

class AgentConversationCreate(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=200)
    course_id: str | None = None

class AgentMessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)
    citations: list | dict = Field(default_factory=list)
    model: str | None = Field(default=None, max_length=100)
