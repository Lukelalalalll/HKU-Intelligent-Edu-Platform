import axios from "axios";

export const DEV_SESSION_STORAGE_KEY = "hku-dev-access-token";
const isDevelopment = import.meta.env.DEV;

export function getDevAccessToken(): string | null {
  if (!isDevelopment || typeof window === "undefined") return null;
  return window.sessionStorage.getItem(DEV_SESSION_STORAGE_KEY);
}

export function setDevAccessToken(token: string | null): void {
  if (!isDevelopment || typeof window === "undefined") return;
  if (token) window.sessionStorage.setItem(DEV_SESSION_STORAGE_KEY, token);
  else window.sessionStorage.removeItem(DEV_SESSION_STORAGE_KEY);
}

export const api = axios.create({ baseURL: "/api", withCredentials: true });
api.interceptors.request.use((config) => {
  if (isDevelopment) {
    config.headers.set("X-HKU-Session-Mode", "isolated");
    const token = getDevAccessToken();
    if (token) config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});
export type Role = "teacher" | "student" | "admin";
export const SUPPORTED_ROLES: Role[] = ["teacher", "student", "admin"];
export type User = { id: string; username: string; email: string; name: string; avatar_url: string | null; role: Role };
export type ProfileUpdate = { name: string; email: string };
export type PasswordChange = { current_password: string; new_password: string };
export type CourseSemester = "semester_1" | "semester_2" | "summer";
export type Course = { id: string; code: string; name: string; description: string; teacher_id: string; teacher_name: string; enrolled_count: number; academic_year_start: number; semester: CourseSemester; timezone: string; schedules: { weekday: number; start_time: string; end_time: string; room: string; timezone?: string | null }[] };
export type MaterialKind = "lecture" | "tutorial";
export type CourseMaterial = { id: string; title: string; file_name: string; mime_type: string; extension: string; size_bytes: number; uploaded_at: string; download_url: string };
export type CourseChapter = { id: string; kind: MaterialKind; title: string; sort_order: number; material_count: number; materials: CourseMaterial[] };
export type Participant = { id: string; name: string; email: string; username?: string; avatar_url?: string | null; enrolled_at?: string };
export type LiveClassSchedule = { meeting_id: string; schedule_id: string; weekday: number; start_time: string; end_time: string; timezone: string; status: string; meeting_number: string; next_start: string | null; next_end: string | null; can_join: boolean; can_start: boolean };
export type LiveClass = { course_id: string; course_name: string; teacher_name: string; timezone: string; schedules: LiveClassSchedule[]; provisioning_required: boolean; status: string };
export type LiveClassAuthorization = { meeting_number: string; sdk_jwt: string; sdk_key: string; zak: string | null; user_name: string; role: number; expires_at: string; join_url: string };
export type Assignment = { id: string; course_id: string; title: string; description: string; due_at: string | null; max_score: number; status: string; course_name?: string; pending_count?: number };
export type TeacherSchedule = { course_id: string; course_code: string; course_name: string; weekday: number; start_time: string; end_time: string; room: string };
export type TeacherDashboardData = { courses: Course[]; schedule: TeacherSchedule[]; pending_assignments: Assignment[] };
export type StudentSchedule = { course_id: string; course_code: string; course_name: string; teacher_name: string; weekday: number; start_time: string; end_time: string; room: string; timezone?: string | null };
export type StudentAssignmentReminder = { id: string; course_id: string; course_name: string; title: string; due_at: string | null; max_score: number; submission_status: "not_started" | "submitted" | "graded" | "overdue"; submitted_at: string | null; score: number | null };
export type StudentDashboardData = { timezone: string; courses: Course[]; schedule: StudentSchedule[]; assignment_reminders: StudentAssignmentReminder[] };
export type AgentMessage = { id: string; conversation_id: string; role: "user" | "assistant"; content: string; citations: unknown[] | Record<string, unknown>; model: string | null; created_at: string };
export type AgentConversation = { id: string; title: string; rag_mode: string; created_at: string; messages?: AgentMessage[] };

export type PptProject = { id: string; title: string; request_text: string; course_id?: string | null; current_stage: "init" | "outline" | "theme" | "layout" | "design" | "export"; status?: string; active_page_id?: string | null; latest_checkpoint_code?: string | null; page_count_target: number | null; theme_id?: string | null; theme_config?: Record<string, any>; layout_assignments?: Record<string, string>; design_status?: "pending" | "running" | "ready" | "failed" | string; page_count: number; cover_preview_url?: string | null; created_at: string; updated_at: string };
export type PptTheme = { id: string; name: string; description: string; family: string; colors: Record<string, string>; layout_count?: number };
export type PptLayout = { id: string; name: string; kind: string };
export type PptElementType = "title" | "body" | "image" | "shape" | "icon" | string;
export type PptSlideElement = {
  id: string;
  type?: PptElementType;
  x: number;
  y: number;
  w: number;
  h: number;
  zIndex?: number;
  text?: string;
  items?: string[];
  font_size?: number;
  font_family?: string;
  font_weight?: number | string;
  align?: "left" | "center" | "right";
  color?: string;
  fill?: string;
  fill_color?: string;
  background?: string;
  background_color?: string;
  stroke?: string;
  stroke_color?: string;
  border_color?: string;
  stroke_width?: number;
  line_width?: number;
  shape?: string;
  src?: string;
  alt?: string;
  opacity?: number;
  radius?: number;
  object_fit?: "cover" | "contain";
  locked?: boolean;
};
export type PptCanvasSpec = { width: 1280; height: 720 };
export type PptDocument = { version?: 2; canvas?: PptCanvasSpec; layout?: string; theme?: Record<string, any>; elements: PptSlideElement[]; speaker_notes?: string };
export type PptPage = { id: string; project_id: string; section_title: string; sort_order: number; title: string; bullets: string[]; statuses: Record<string, string>; search_queries: { query_text: string; query_purpose?: string }[]; summary_md: string; citations: any[]; document: PptDocument | null; document_revision?: number; current_document_version_id?: string | null; speaker_notes: string; page_role?: string; content_plan?: Record<string, any>; visual_plan?: Record<string, any>; preview_url?: string | null; layout_id?: string | null };
export type PptGenerationJob = { id: string; project_id: string; status: string; stage: string; total_pages: number; completed_pages: number; failed_pages: number; current_page_id?: string | null; error_message?: string | null };
export type PptMessage = { id: string; role: "user" | "assistant"; stage: string; scope_type: string; page_id?: string | null; content_md: string; payload?: Record<string, any>; created_at: string };
export type PptRequirement = { project_id: string; status: string; page_count_target: number | null; answers: Record<string, any>; questions: { code?: string; label: string; options?: string[] }[]; page_count_options: any[]; ready_to_outline?: boolean; suggested_additions?: string[]; brief_summary?: string };
export type PptSource = { id: string; title: string; source_type: string; metadata?: Record<string, any>; collection_id: string };
export type RequirementChatResponse = { project_id: string; message: PptMessage; status: string; answers: Record<string, any>; question?: { code?: string; label: string; options?: string[] } | null; ready_to_outline: boolean; missing_fields: string[]; suggested_additions: string[]; brief_summary?: string; attachments: PptSource[] };
export type PptProviderConfig = { base_url: string; api_key_configured: boolean; api_key_masked: string; model: string; embedding_model: string; timeout_seconds: number };
export type PptChatTrace = { kind?: string; round?: number; tool?: string; status?: string; message?: string; slideIndex?: number };
export type PptChatStreamEvent = { type: "status" | "trace" | "chunk" | "complete" | "error"; status?: string; trace?: PptChatTrace; chunk?: string; detail?: string; chat?: { response?: string; tool_calls?: string[]; message_id?: string }; requirement?: RequirementChatResponse };
export const profileApi = {
  get: () => api.get<User>("/profile"),
  update: (payload: ProfileUpdate) => api.patch<User>("/profile", payload),
  uploadAvatar: (file: File) => { const form = new FormData(); form.append("file", file); return api.post<User>("/profile/avatar", form); },
  removeAvatar: () => api.delete<User>("/profile/avatar"),
  changePassword: (payload: PasswordChange) => api.put("/profile/password", payload),
};
export const liveClassApi = {
  get: (courseId: string) => api.get<LiveClass>(`/courses/${courseId}/live-class`),
  provision: (courseId: string) => api.post<LiveClass>(`/courses/${courseId}/live-class/provision`),
  authorize: (courseId: string, action: "start" | "join", meetingId?: string) => api.post<LiveClassAuthorization>(`/courses/${courseId}/live-class/authorize`, { action, meeting_id: meetingId }),
};
export const participantApi = {
  list: (courseId: string) => api.get<Participant[]>(`/courses/${courseId}/participants`),
};
export const courseMaterialsApi = {
  list: (courseId: string, kind: MaterialKind) => api.get<CourseChapter[]>(`/courses/${courseId}/materials`, { params: { kind } }),
  createChapter: (courseId: string, payload: { kind: MaterialKind; title: string }) => api.post<CourseChapter>(`/courses/${courseId}/materials/chapters`, payload),
  updateChapter: (courseId: string, chapterId: string, payload: { title?: string; sort_order?: number }) => api.patch<CourseChapter>(`/courses/${courseId}/materials/chapters/${chapterId}`, payload),
  deleteChapter: (courseId: string, chapterId: string) => api.delete(`/courses/${courseId}/materials/chapters/${chapterId}`),
  upload: (courseId: string, chapterId: string, file: File, title?: string) => { const form = new FormData(); form.append("file", file); if (title) form.append("title", title); return api.post<CourseMaterial>(`/courses/${courseId}/materials/chapters/${chapterId}/files`, form); },
  delete: (courseId: string, materialId: string) => api.delete(`/courses/${courseId}/materials/${materialId}`),
  download: (courseId: string, materialId: string) => api.get<Blob>(`/courses/${courseId}/materials/${materialId}/download`, { responseType: "blob" }),
};
export const studentApi = {
  dashboard: () => api.get<StudentDashboardData>("/student/dashboard"),
};
export const pptApi = {
  projects: () => api.get<{ items: PptProject[] }>("/ppt/projects"),
  preview: (url: string) => api.get<Blob>(url.replace(/^\/api/, ""), { responseType: "blob" }),
  createProject: (payload: { title: string; request_text: string; course_id?: string }) => api.post<PptProject>("/ppt/projects", payload),
  project: (id: string) => api.get<PptProject>(`/ppt/projects/${id}`),
  deleteProject: (id: string) => api.delete(`/ppt/projects/${id}`),
  provider: () => api.get<PptProviderConfig>("/ppt/settings/provider"),
  saveProvider: (payload: { base_url: string; api_key?: string; model: string; embedding_model: string; timeout_seconds: number }) => api.patch("/ppt/settings/provider", payload),
  testProvider: () => api.post("/ppt/settings/provider/test"),
  clearProvider: () => api.delete("/ppt/settings/provider"),
  requirements: (id: string) => api.get<PptRequirement>(`/ppt/projects/${id}/requirements`),
  requirementChat: (id: string, payload: { content?: string; option_id?: string; option_label?: string; bootstrap?: boolean }) => api.post<RequirementChatResponse>(`/ppt/projects/${id}/requirements/chat`, payload),
  streamRequirementChat: async (id: string, payload: { content?: string; option_id?: string; option_label?: string; bootstrap?: boolean }, handlers: { onEvent?: (event: PptChatStreamEvent) => void } = {}, signal?: AbortSignal) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (isDevelopment) { headers["X-HKU-Session-Mode"] = "isolated"; const token = getDevAccessToken(); if (token) headers.Authorization = `Bearer ${token}`; }
    const response = await fetch(`/api/ppt/projects/${id}/requirements/chat/stream`, { method: "POST", headers, credentials: "include", body: JSON.stringify(payload), signal });
    if (!response.ok || !response.body) throw new Error((await response.text()) || "需求流连接失败");
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ""; let complete: PptChatStreamEvent | undefined;
    const consume = (frame: string) => { const data = frame.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n"); if (!data) return; const event = JSON.parse(data) as PptChatStreamEvent; handlers.onEvent?.(event); if (event.type === "complete") complete = event; if (event.type === "error") throw new Error(event.detail || "需求访谈失败"); };
    while (true) { const { done, value } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); let split = buffer.indexOf("\n\n"); while (split >= 0) { consume(buffer.slice(0, split)); buffer = buffer.slice(split + 2); split = buffer.indexOf("\n\n"); } }
    if (buffer.trim()) consume(buffer); return complete;
  },
  generateRequirements: (id: string) => api.post(`/ppt/projects/${id}/requirements:generate`),
  patchRequirements: (id: string, payload: any) => api.patch(`/ppt/projects/${id}/requirements`, payload),
  generateOutline: (id: string, payload: { page_count_target: number }) => api.post(`/ppt/projects/${id}/outline:generate`, payload),
  themes: () => api.get<{ items: PptTheme[] }>("/ppt/themes"),
  layouts: (themeId: string) => api.get<{ items: PptLayout[] }>(`/ppt/themes/${themeId}/layouts`),
  selectTheme: (id: string, theme_id: string) => api.post<PptProject>(`/ppt/projects/${id}/theme`, { theme_id }),
  assignLayouts: (id: string, assignments: Record<string, string>, mode: "manual" | "auto") => api.put(`/ppt/projects/${id}/layouts`, { assignments, mode }),
  generateDesign: (id: string) => api.post<PptGenerationJob>(`/ppt/projects/${id}/design:generate`),
  generationJob: (id: string, jobId: string) => api.get<PptGenerationJob>(`/ppt/projects/${id}/generation-jobs/${jobId}`),
  retryGeneration: (id: string, jobId: string) => api.post<PptGenerationJob>(`/ppt/projects/${id}/generation-jobs/${jobId}:retry`),
  cancelGeneration: (id: string, jobId: string) => api.post<PptGenerationJob>(`/ppt/projects/${id}/generation-jobs/${jobId}:cancel`),
  pages: (id: string) => api.get<{ items: PptPage[] }>(`/ppt/projects/${id}/pages`),
  page: (id: string, pageId: string) => api.get<PptPage>(`/ppt/projects/${id}/pages/${pageId}`),
  patchPage: (id: string, pageId: string, payload: any) => api.patch<PptPage>(`/ppt/projects/${id}/pages/${pageId}`, payload),
  action: (id: string, pageId: string, action_type: string) => api.post(`/ppt/projects/${id}/pages/${pageId}/actions`, { action_type }),
  batch: (id: string, action_type: string) => api.post(`/ppt/projects/${id}/actions/batch`, { action_type }),
  upload: (id: string, file: File, pageId?: string) => { const form = new FormData(); form.append("file", file); return api.post(`/ppt/projects/${id}/files`, form, { params: pageId ? { page_id: pageId } : undefined }); },
  export: (id: string) => api.post<{ id: string; status: string }>(`/ppt/projects/${id}/exports`, {}),
  exportStatus: (id: string, exportId: string) => api.get<{ id: string; status: string; error?: string }>(`/ppt/projects/${id}/exports/${exportId}`),
  streamUrl: (id: string) => `/api/ppt/projects/${id}/events/stream`,
  messages: (id: string, pageId?: string) => api.get<{ items: PptMessage[] }>(`/ppt/projects/${id}/messages`, { params: pageId ? { page_id: pageId } : undefined }),
  message: (id: string, content: string, pageId?: string, extra?: { option_id?: string; option_label?: string }) => api.post<{ user: PptMessage; assistant: PptMessage }>(`/ppt/projects/${id}/messages`, { content, page_id: pageId, ...extra }),
  streamMessage: async (id: string, payload: { content: string; page_id?: string; ui_surface?: string }, handlers: { onEvent?: (event: PptChatStreamEvent) => void } = {}, signal?: AbortSignal) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (isDevelopment) {
      headers["X-HKU-Session-Mode"] = "isolated";
      const token = getDevAccessToken();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    const response = await fetch(`/api/ppt/projects/${id}/messages/stream`, { method: "POST", headers, credentials: "include", body: JSON.stringify(payload), signal });
    if (!response.ok || !response.body) throw new Error((await response.text()) || "消息流连接失败");
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ""; let complete: PptChatStreamEvent | undefined;
    const consume = (frame: string) => { const data = frame.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n"); if (!data) return; try { const event = JSON.parse(data) as PptChatStreamEvent; handlers.onEvent?.(event); if (event.type === "complete") complete = event; if (event.type === "error") throw new Error(event.detail || "Agent 执行失败"); } catch (error) { if (error instanceof SyntaxError) return; throw error; } };
    while (true) { const { done, value } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); let split = buffer.indexOf("\n\n"); while (split >= 0) { consume(buffer.slice(0, split)); buffer = buffer.slice(split + 2); split = buffer.indexOf("\n\n"); } }
    if (buffer.trim()) consume(buffer);
    return complete;
  },
  sources: (id: string) => api.get<{ items: PptSource[] }>(`/ppt/projects/${id}/sources`),
  checkpoints: (id: string) => api.get(`/ppt/projects/${id}/checkpoints`),
  confirmCheckpoint: (id: string, code: string, note?: string) => api.post(`/ppt/projects/${id}/checkpoints/${code}:confirm`, { note }),
  patchDocument: (id: string, pageId: string, document: PptDocument, revision: number) => api.patch<PptPage>(`/ppt/projects/${id}/pages/${pageId}/document`, { document, revision }),
  restoreDocument: (id: string, pageId: string, direction: "undo" | "redo", revision: number) => api.post<PptPage>(`/ppt/projects/${id}/pages/${pageId}/document:${direction}`, { document: {}, revision }),
  patchStoryboard: (id: string, pageIds: string[]) => api.patch<{ items: PptPage[] }>(`/ppt/projects/${id}/storyboard`, { page_ids: pageIds }),
  downloadExport: (id: string, exportId: string) => api.get<Blob>(`/ppt/projects/${id}/exports/${exportId}/download`, { responseType: "blob" }),
};
