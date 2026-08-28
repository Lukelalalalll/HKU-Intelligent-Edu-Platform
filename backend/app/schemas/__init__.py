from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["teacher", "student", "admin"]

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

class ScheduleIn(BaseModel):
    weekday: int = Field(ge=1, le=7)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    room: str = ""

class CourseCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    schedules: list[ScheduleIn] = Field(default_factory=list)

class CourseOut(BaseModel):
    id: str
    code: str
    name: str
    description: str
    teacher_id: str
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
