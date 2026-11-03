/**
 * Lesson plan agent endpoint and type re-exports.
 *
 * Kept as a thin domain module so feature code can import from ``api/domains``
 * without reaching into the monolithic ``api.ts`` barrel.
 */
export { lessonPlanApi } from "../../api";
export type {
  LessonPlanAsset,
  LessonPlanCapabilities,
  LessonPlanChatComplete,
  LessonPlanChatHandlers,
  LessonPlanChatStreamEvent,
  LessonPlanExportJob,
  LessonPlanGenerateResult,
  LessonPlanMessage,
  LessonPlanMessagePayload,
  LessonPlanPage,
  LessonPlanPageDocument,
  LessonPlanProject,
  LessonPlanQuestion,
  LessonPlanStage,
  LessonPlanState,
} from "../../api";
