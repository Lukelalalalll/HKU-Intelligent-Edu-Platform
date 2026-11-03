/**
 * Route table for the application shell.
 *
 * Feature pages are lazy chunks; guarded routes redirect to ``/login`` and the
 * role gates bounce users to their own landing page.
 */
import React, { Suspense, lazy, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useI18n } from "../i18n";
import { useAuth } from "../store";
const PptCoursewareAgent = lazy(() => import("../ppt/CoursewareAgent"));
const CoursesRoute = lazy(() => import("../features/courses/routes/CoursesRoute"));
const CourseDetailRoute = lazy(() => import("../features/courses/routes/CourseDetailRoute"));
const LiveClassRoute = lazy(() => import("../features/courses/routes/LiveClassRoute"));
const ProfileRoute = lazy(() => import("../features/profile/routes/ProfileRoute"));
const CoursewareAgentRoute = lazy(() => import("../features/courseware/CoursewareAgentRoute"));
const LessonPlanAgentRoute = lazy(() => import("../features/lessonPlan/LessonPlanAgentRoute"));
const AiVideoRoute = lazy(() => import("../features/aiVideo/routes/AiVideoRoute"));
const AiVideoProjectRoute = lazy(() => import("../features/aiVideo/routes/AiVideoProjectRoute"));
import AuthPage from "./components/AuthPage";
import Shell from "./components/Shell";
import { Protected, RoleGate, HomeRoute } from "./guards";
import { Dashboard, StudentDashboard } from "./pages/DashboardPages";
import GradingPlaceholder from "./pages/GradingPlaceholder";
import CoursewareAgent from "./pages/CoursewareAgentPage";
import Admin from "./pages/AdminPage";

/**
 * Application route tree with lazy feature chunks and auth bootstrap.
 */
export default function App() {
  const bootstrap = useAuth((state) => state.bootstrap);
  const { t } = useI18n();
  useEffect(() => { bootstrap(); }, [bootstrap]);
  return <Suspense fallback={<div className="loading-screen">{t("common.app.loadingWorkspace")}</div>}><Routes><Route path="/login" element={<AuthPage mode="login" />} /><Route path="/register" element={<AuthPage mode="register" />} /><Route element={<Protected />}><Route path="/" element={<HomeRoute />} /><Route path="/student" element={<RoleGate roles={["student"]}><StudentDashboard /></RoleGate>} /><Route path="/courseware-agent" element={<RoleGate roles={["student"]}><CoursewareAgentRoute /></RoleGate>} /><Route path="/teacher" element={<RoleGate roles={["teacher"]}><Dashboard /></RoleGate>} /><Route path="/teacher/courseware-agent" element={<RoleGate roles={["teacher"]}><PptCoursewareAgent /></RoleGate>} /><Route path="/teacher/courseware-agent/:projectId" element={<RoleGate roles={["teacher"]}><PptCoursewareAgent /></RoleGate>} /><Route path="/teacher/lesson-plan-agent" element={<RoleGate roles={["teacher"]}><LessonPlanAgentRoute /></RoleGate>} /><Route path="/teacher/lesson-plan-agent/:projectId" element={<RoleGate roles={["teacher"]}><LessonPlanAgentRoute /></RoleGate>} /><Route path="/teacher/ai-video" element={<RoleGate roles={["teacher"]}><AiVideoRoute /></RoleGate>} /><Route path="/teacher/ai-video/:projectId" element={<RoleGate roles={["teacher"]}><AiVideoProjectRoute /></RoleGate>} /><Route path="/admin" element={<RoleGate roles={["admin"]}><Admin /></RoleGate>} /><Route path="/courses" element={<CoursesRoute />} /><Route path="/courses/:courseId" element={<CourseDetailRoute />} /><Route path="/courses/:courseId/live" element={<LiveClassRoute />} /><Route path="/assignments/:assignmentId/grading" element={<GradingPlaceholder />} /><Route path="/profile" element={<ProfileRoute />} /></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes></Suspense>;
}
