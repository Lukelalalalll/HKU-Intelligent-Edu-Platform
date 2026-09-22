import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { getApiErrorMessage, type Course, type LiveClassSchedule, type MaterialKind } from "../../../api";
import { useAuth } from "../../../store";
import { useCourseAssignmentsQuery, useLiveClassQuery, useMaterialsQuery, useParticipantsQuery, useProvisionLiveClassMutation } from "../../../hooks/useCourseQueries";
import { SEMESTER_LABELS } from "../courseTerms";
import styles from "../styles/CoursesRoute.module.css";
import DiscussionModule from "./DiscussionModule";
import { AssignmentsModule, MaterialsModule, ParticipantModule } from "./CourseModuleViews";

const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const formatTime = (value: string | null) => value ? new Intl.DateTimeFormat("zh-CN", { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "暂无下一课次";

export const courseSidebarItems = ["Announcements", "Assignments", "Discussions", "Grades", "Participant", "Syllabus", "Lecture Files", "Tutorial File", "Zoom"];
const sidebarItems = courseSidebarItems;
const zoomTabs = [
  { id: "upcoming", label: "Upcoming Meetings" },
  { id: "previous", label: "Previous Meetings" },
  { id: "recordings", label: "Cloud Recordings" },
  { id: "summary", label: "Meeting Summary" },
] as const;

export default function LiveClassPanel({ courseId, course }: { courseId: string; course?: Course }) {
  const user = useAuth((state) => state.user);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<(typeof zoomTabs)[number]["id"]>("upcoming");
  const [activeModule, setActiveModule] = useState(() => searchParams.get("module") || "Zoom");
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);
  const materialKind: MaterialKind | null = activeModule === "Lecture Files" ? "lecture" : activeModule === "Tutorial File" ? "tutorial" : null;
  useEffect(() => {
    const module = searchParams.get("module");
    if (module && sidebarItems.includes(module) && module !== activeModule) setActiveModule(module);
  }, [activeModule, searchParams]);
  const liveClassQuery = useLiveClassQuery(courseId, activeModule === "Zoom");
  const participantsQuery = useParticipantsQuery(courseId, activeModule === "Participant");
  const materialsQuery = useMaterialsQuery(courseId, materialKind || undefined);
  const assignmentsQuery = useCourseAssignmentsQuery(courseId, activeModule === "Assignments");
  const provisionMutation = useProvisionLiveClassMutation(courseId);
  const liveClass = liveClassQuery.data;
  const participants = participantsQuery.data ?? [];
  const materials = materialsQuery.data ?? [];
  const assignments = assignmentsQuery.data ?? [];
  const setModule = (module: string) => {
    setActiveModule(module);
    setSelectedChapterId(null);
    setSearchParams((current) => { const next = new URLSearchParams(current); next.set("module", module); return next; }, { replace: true });
  };

  const provision = async () => {
    try { await provisionMutation.mutateAsync(); toast.success("课堂会议已准备"); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, "Zoom 会议准备失败")); }
  };

  if (liveClassQuery.isLoading && activeModule === "Zoom") return <section className={styles.zoomState}><i className="fas fa-circle-notch fa-spin" /><strong>正在检查 Zoom 课堂状态…</strong></section>;
  const isTeacher = user?.role === "teacher" || user?.role === "admin";
  const termLabel = course ? `${course.academic_year_start}/${String(course.academic_year_start + 1).slice(-2)} · ${SEMESTER_LABELS[course.semester]}` : "Course workspace";
  return <section className={styles.zoomWorkspace} aria-label="Zoom 课程工作区">
    <aside className={styles.zoomSidebar}>
      <div className={styles.zoomSidebarBrand}><span className={styles.zoomSidebarMenu}><i className="fas fa-bars" /></span><div><strong>{course?.code || "COURSE"}</strong><small>{course?.name || "Zoom workspace"}</small></div></div>
      <div className={styles.zoomSidebarTerm}>{termLabel}</div>
      <nav className={styles.zoomCourseNav} aria-label="课程导航">
        {sidebarItems.map((item) => <a href={`?module=${encodeURIComponent(item)}`} key={item} className={activeModule === item ? styles.zoomCourseNavActive : ""} aria-current={activeModule === item ? "page" : undefined} onClick={(event) => { event.preventDefault(); setModule(item); }}><i className={`fas ${item === "Zoom" ? "fa-video" : item === "Participant" ? "fa-user-group" : item.includes("File") ? "fa-folder-open" : "fa-circle-dot"}`} />{item}</a>)}
      </nav>
    </aside>
    <div className={`${styles.zoomMain} ${activeModule === "Zoom" ? styles.zoomMainZoom : styles.zoomMainHku} ${activeModule === "Participant" ? styles.zoomMainParticipant : ""} ${activeModule === "Discussions" ? styles.zoomMainDiscussion : ""} ${materialKind ? styles.zoomMainMaterials : ""}`}>
      {activeModule === "Zoom" ? !liveClass ? <section className={styles.zoomState}><i className="fas fa-circle-exclamation" /><strong>暂时无法加载课堂状态</strong><span>{liveClassQuery.isError ? getApiErrorMessage(liveClassQuery.error, "请稍后重试。") : "请稍后重试。"}</span><button type="button" className="secondary-action" onClick={() => void liveClassQuery.refetch()}>重试</button></section> : <>
        <header className={styles.zoomTopbar}>
          <div className={styles.zoomWordmark}>zoom</div>
          <nav className={styles.zoomProductNav} aria-label="Zoom 导航"><span className={styles.zoomProductNavActive}><i className="fas fa-house" /> Home</span><span><i className="fas fa-file-lines" /> Docs</span><span><i className="fas fa-wand-magic-sparkles" /> ZoomMate <b>NEW</b></span></nav>
        </header>
        <div className={styles.zoomContent}>
        <div className={styles.zoomTimezone}>Your current Time Zone and Language are ({liveClass.timezone}) Hong Kong, English <i className="fas fa-pen" aria-hidden="true" /></div>
        <div className={styles.zoomWorkspaceHeading}><div><p className="eyebrow">LIVE CLASS</p><h2>Zoom 实时课堂</h2><span>教师：{liveClass.teacher_name}</span></div><span className={`${styles.liveStatus} ${liveClass.status === "live" ? styles.liveStatusActive : ""}`}><i className="fas fa-circle" /> {liveClass.status === "live" ? "进行中" : "按课表开放"}</span></div>
        <div className={styles.zoomMeetingTabs} role="tablist" aria-label="会议记录分类">
          {zoomTabs.map((tab) => <button type="button" role="tab" aria-selected={activeTab === tab.id} className={activeTab === tab.id ? styles.zoomMeetingTabActive : ""} onClick={() => setActiveTab(tab.id)} key={tab.id}>{tab.id === "summary" && <i className="fas fa-sparkles" />}{tab.label}</button>)}
        </div>
        {activeTab === "upcoming" ? <div className={styles.zoomTableCard}>
          <div className={styles.zoomTableHeader}><span>Start Time</span><span>Topic</span><span>Meeting ID</span><span>Actions</span></div>
          {liveClass.schedules.length ? liveClass.schedules.map((schedule) => <LiveScheduleRow key={schedule.schedule_id} schedule={schedule} topic={course?.name || "Course meeting"} isTeacher={isTeacher} onOpen={(action) => navigate(`/courses/${courseId}/live?meetingId=${encodeURIComponent(schedule.meeting_id)}&action=${action}`)} />) : <div className={styles.zoomNoData}>No Data</div>}
        </div> : <div className={styles.zoomNoDataPanel}><i className="fas fa-inbox" /><strong>No Data</strong><span>暂无可显示的会议记录。</span></div>}
        {liveClass.provisioning_required && isTeacher && <button className="primary-action" type="button" disabled={provisionMutation.isPending} onClick={provision}><i className={`fas ${provisionMutation.isPending ? "fa-circle-notch fa-spin" : "fa-video"}`} />{provisionMutation.isPending ? "准备中…" : "准备 Zoom 课堂"}</button>}
        {liveClass.provisioning_required && user?.role === "student" && <div className={styles.zoomNotice}><i className="fas fa-circle-info" /> 教师尚未准备 Zoom 课堂，准备完成后即可加入。</div>}
        </div>
      </> : activeModule === "Assignments" ? <AssignmentsModule courseId={courseId} assignments={assignments} loading={assignmentsQuery.isLoading} error={assignmentsQuery.isError} isTeacher={isTeacher} onRefresh={() => assignmentsQuery.refetch().then(() => undefined)} onGrade={(id) => navigate(`/assignments/${id}/grading`)} /> : activeModule === "Discussions" ? <DiscussionModule courseId={courseId} /> : activeModule === "Participant" ? <ParticipantModule participants={participants} loading={participantsQuery.isLoading} error={participantsQuery.isError} isTeacher={isTeacher} currentUserId={user?.id} /> : materialKind ? <MaterialsModule courseId={courseId} kind={materialKind} chapters={materials} loading={materialsQuery.isLoading} error={materialsQuery.isError} selectedChapterId={selectedChapterId} onSelectChapter={setSelectedChapterId} onRefresh={() => materialsQuery.refetch().then(() => undefined)} isTeacher={isTeacher} /> : <div className={styles.courseModulePlaceholder}><p className="eyebrow">COURSE MODULE</p><h2>{activeModule}</h2><p>这是课程导航预留的 HKU 工作区。选择左侧 Zoom 后可查看实时课堂和会议安排。</p></div>}
    </div>
  </section>;
}

function LiveScheduleRow({ schedule, topic, isTeacher, onOpen }: { schedule: LiveClassSchedule; topic: string; isTeacher: boolean; onOpen: (action: "start" | "join") => void }) {
  const action = schedule.can_start ? "start" : "join";
  const enabled = schedule.can_join || schedule.can_start;
  return <div className={styles.zoomTableRow}><span className={styles.zoomMeetingTime}>{formatTime(schedule.next_start)}<small>{weekdays[schedule.weekday - 1] || `周${schedule.weekday}`} · {schedule.start_time} – {schedule.end_time}</small></span><span className={styles.zoomMeetingTopic}>{topic}<small>{schedule.status === "unconfigured" ? "未配置" : schedule.status}</small></span><span className={styles.zoomMeetingId}>{schedule.meeting_number || "—"}</span><span><button className={enabled ? "primary-action" : "secondary-action"} type="button" disabled={!enabled} onClick={() => onOpen(action)}><i className={`fas ${isTeacher && action === "start" ? "fa-chalkboard-user" : "fa-arrow-right-to-bracket"}`} />{isTeacher && action === "start" ? "开始课堂" : enabled ? "加入课堂" : "未开放"}</button></span></div>;
}













