"""Stable model re-exports; domain implementations live in explicit modules."""
from .identity import AiBusinessBinding, AiProvider, AuditLog, User, UserRole
from .courses import Course, CourseChapter, CourseMaterial, CourseMaterialChunk, CourseMaterialIngestion, CourseSchedule, CourseZoomMeeting, Enrollment, LessonPlanAsset, LessonPlanEvent, LessonPlanExportJob, LessonPlanMessage, LessonPlanPage, LessonPlanProject, RecordingSession
from .assignments import Assignment, AssignmentAttachment, Submission
from .files import AgentMessageAttachment, FileAsset, FileContextBinding, FileProcessingChunk, FileProcessingDocument, FileProcessingJob, FileProcessingPage, SubmissionAttachment
from .discussions import DiscussionComment, DiscussionLike
from .ppt_domain import PptAgentEvent, PptAgentRun, PptCheckpoint, PptDocumentVersion, PptEditorAsset, PptExportJob, PptGenerationJob, PptMessage, PptOutlineVersion, PptPage, PptProject, PptProviderConfig, PptRequirement, PptSourceChunk, PptSourceCollection, PptSourceDocument
from .video import VideoAsset, VideoGenerationJob, VideoProject, VideoScene, VideoSource
from .jobs import TaskOutbox
from .entities import AgentConversation, AgentMessage

__all__ = ["User", "UserRole", "Course", "Enrollment", "CourseSchedule", "Assignment", "AssignmentAttachment", "Submission", "FileAsset", "CourseChapter", "CourseMaterial", "CourseMaterialIngestion", "CourseMaterialChunk", "DiscussionComment", "DiscussionLike", "RecordingSession", "CourseZoomMeeting", "AgentConversation", "AgentMessage", "AuditLog", "PptProject", "PptRequirement", "PptOutlineVersion", "PptPage", "PptSourceCollection", "PptSourceDocument", "PptSourceChunk", "PptAgentRun", "PptAgentEvent", "PptProviderConfig", "PptExportJob", "PptMessage", "PptCheckpoint", "PptDocumentVersion", "PptGenerationJob", "PptEditorAsset", "LessonPlanProject", "LessonPlanPage", "LessonPlanAsset", "LessonPlanEvent", "LessonPlanExportJob", "LessonPlanMessage", "AiProvider", "AiBusinessBinding", "FileProcessingDocument", "FileProcessingJob", "FileProcessingPage", "FileProcessingChunk", "FileContextBinding", "AgentMessageAttachment", "SubmissionAttachment", "TaskOutbox", "VideoProject", "VideoSource", "VideoScene", "VideoGenerationJob", "VideoAsset"]
