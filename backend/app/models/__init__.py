from app.models.entities import (
    AgentConversation,
    AgentMessage,
    Assignment, AssignmentAttachment,
    AuditLog,
    Course,
    CourseSchedule,
    CourseZoomMeeting,
    CourseChapter,
    CourseMaterial,
    CourseMaterialIngestion,
    CourseMaterialChunk,
    DiscussionComment,
    DiscussionLike,
    Enrollment,
    FileAsset,
    RecordingSession,
    Submission,
    User,
    UserRole,
)
from app.models.ppt import (
    PptAgentEvent, PptAgentRun, PptExportJob, PptOutlineVersion, PptPage,
    PptProject, PptRequirement, PptSourceChunk,
    PptSourceCollection, PptSourceDocument,
    PptMessage, PptCheckpoint, PptDocumentVersion, PptGenerationJob, PptEditorAsset,
)
from app.models.lesson_plan import LessonPlanProject, LessonPlanPage, LessonPlanAsset, LessonPlanEvent, LessonPlanExportJob
from app.models.ai import AiProvider, AiBusinessBinding
from app.models.file_processing import FileProcessingDocument, FileProcessingJob, FileProcessingPage, FileProcessingChunk, FileContextBinding, AgentMessageAttachment, SubmissionAttachment
from app.models.jobs import TaskOutbox

__all__ = [
    "User", "UserRole", "Course", "Enrollment", "CourseSchedule", "Assignment", "AssignmentAttachment", "Submission",
    "FileAsset", "CourseChapter", "CourseMaterial", "CourseMaterialIngestion", "CourseMaterialChunk", "DiscussionComment", "DiscussionLike", "RecordingSession", "CourseZoomMeeting", "AgentConversation", "AgentMessage", "AuditLog",
    "PptProject", "PptRequirement", "PptOutlineVersion", "PptPage",
    "PptSourceCollection", "PptSourceDocument", "PptSourceChunk",
    "PptAgentRun", "PptAgentEvent", "PptExportJob",
    "PptMessage", "PptCheckpoint", "PptDocumentVersion", "PptGenerationJob", "PptEditorAsset",
    "LessonPlanProject", "LessonPlanPage", "LessonPlanAsset", "LessonPlanEvent", "LessonPlanExportJob",
    "AiProvider", "AiBusinessBinding",
    "FileProcessingDocument", "FileProcessingJob", "FileProcessingPage", "FileProcessingChunk", "FileContextBinding", "AgentMessageAttachment", "SubmissionAttachment",
    "TaskOutbox",
]

