import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { getApiErrorMessage, type Course, type LiveClassSchedule, type MaterialKind } from "../../../api";
import { useAuth } from "../../../store";
import { useI18n, type TranslationKey } from "../../../i18n";
import { useCourseAssignmentsQuery, useLiveClassQuery, useMaterialsQuery, useParticipantsQuery, useProvisionLiveClassMutation } from "../../../hooks/useCourseQueries";
import { formatSemesterLabel, formatWeekdayLabel } from "../courseTerms";
import styles from "../styles/CoursesRoute.module.css";
import DiscussionModule from "./DiscussionModule";
import { AssignmentsModule, MaterialsModule, ParticipantModule } from "./CourseModuleViews";

/**
 * Modules shown in the course workspace navigation.
 *
 * The values double as stable module identifiers (``?module=`` query values),
 * so they stay English; {@link sidebarItemLabelKeys} maps them to display copy.
 */
export const courseSidebarItems = ["Announcements", "Assignments", "Discussions", "Grades", "Participant", "Syllabus", "Lecture Files", "Tutorial File", "Zoom"];
const sidebarItems = courseSidebarItems;
const sidebarItemLabelKeys: Record<string, TranslationKey> = {
  Announcements: "courses.nav.announcements",
  Assignments: "courses.nav.assignments",
  Discussions: "courses.nav.discussions",
  Grades: "courses.nav.grades",
  Participant: "courses.nav.participants",
  Syllabus: "courses.nav.syllabus",
  "Lecture Files": "courses.nav.lectureFiles",
  "Tutorial File": "courses.nav.tutorialFiles",
  Zoom: "courses.nav.zoom",
};
const zoomTabs = [
  { id: "upcoming", labelKey: "courses.live.tabs.upcoming" },
  { id: "previous", labelKey: "courses.live.tabs.previous" },
  { id: "recordings", labelKey: "courses.live.tabs.recordings" },
  { id: "summary", labelKey: "courses.live.tabs.summary" },
] as const satisfies readonly { id: string; labelKey: TranslationKey }[];

/**
 * Course workspace with Zoom, materials, assignments and discussion tabs.
 *
 * The active module is mirrored into the ``module`` query parameter.
 */
export default function LiveClassPanel({ courseId, course }: { courseId: string; course?: Course }) {
  const user = useAuth((state) => state.user);
  const { t } = useI18n();
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
  const moduleLabelKey = sidebarItemLabelKeys[activeModule];
  const setModule = (module: string) => {
    setActiveModule(module);
    setSelectedChapterId(null);
    setSearchParams((current) => { const next = new URLSearchParams(current); next.set("module", module); return next; }, { replace: true });
  };

  const provision = async () => {
    try { await provisionMutation.mutateAsync(); toast.success(t("courses.live.prepared")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("courses.live.prepareFailed"))); }
  };

  if (liveClassQuery.isLoading && activeModule === "Zoom") return <section className={styles.zoomState}><i className="fas fa-circle-notch fa-spin" /><strong>{t("courses.live.loading")}</strong></section>;
  const isTeacher = user?.role === "teacher" || user?.role === "admin";
  const termLabel = course ? `${course.academic_year_start}/${String(course.academic_year_start + 1).slice(-2)} · ${formatSemesterLabel(course.semester, t)}` : t("courses.live.courseWorkspace");
  return <section className={styles.zoomWorkspace} aria-label={t("courses.live.workspaceAria")}>
    <aside className={styles.zoomSidebar}>
      <div className={styles.zoomSidebarBrand}><span className={styles.zoomSidebarMenu}><i className="fas fa-bars" /></span><div><strong>{course?.code || "COURSE"}</strong><small>{course?.name || t("courses.live.zoomWorkspace")}</small></div></div>
      <div className={styles.zoomSidebarTerm}>{termLabel}</div>
      <nav className={styles.zoomCourseNav} aria-label={t("courses.live.courseNavAria")}>
        {sidebarItems.map((item) => <a href={`?module=${encodeURIComponent(item)}`} key={item} className={activeModule === item ? styles.zoomCourseNavActive : ""} aria-current={activeModule === item ? "page" : undefined} onClick={(event) => { event.preventDefault(); setModule(item); }}><i className={`fas ${item === "Zoom" ? "fa-video" : item === "Participant" ? "fa-user-group" : item.includes("File") ? "fa-folder-open" : "fa-circle-dot"}`} />{t(sidebarItemLabelKeys[item])}</a>)}
      </nav>
    </aside>
    <div className={`${styles.zoomMain} ${activeModule === "Zoom" ? styles.zoomMainZoom : styles.zoomMainHku} ${activeModule === "Participant" ? styles.zoomMainParticipant : ""} ${activeModule === "Discussions" ? styles.zoomMainDiscussion : ""} ${materialKind ? styles.zoomMainMaterials : ""}`}>
      {activeModule === "Zoom" ? !liveClass ? <section className={styles.zoomState}><i className="fas fa-circle-exclamation" /><strong>{t("courses.live.loadError")}</strong><span>{liveClassQuery.isError ? getApiErrorMessage(liveClassQuery.error, t("courses.common.retryHint")) : t("courses.common.retryHint")}</span><button type="button" className="secondary-action" onClick={() => void liveClassQuery.refetch()}>{t("common.actions.retry")}</button></section> : <>
        <header className={styles.zoomTopbar}>
          <div className={styles.zoomWordmark}>zoom</div>
          <nav className={styles.zoomProductNav} aria-label={t("courses.live.zoomNavAria")}><span className={styles.zoomProductNavActive}><i className="fas fa-house" /> Home</span><span><i className="fas fa-file-lines" /> Docs</span><span><i className="fas fa-wand-magic-sparkles" /> ZoomMate <b>NEW</b></span></nav>
        </header>
        <div className={styles.zoomContent}>
        <div className={styles.zoomTimezone}>{t("courses.live.timezone", { timezone: liveClass.timezone })} <i className="fas fa-pen" aria-hidden="true" /></div>
        <div className={styles.zoomWorkspaceHeading}><div><p className="eyebrow">LIVE CLASS</p><h2>{t("courses.live.title")}</h2><span>{t("courses.live.teacher", { name: liveClass.teacher_name })}</span></div><span className={`${styles.liveStatus} ${liveClass.status === "live" ? styles.liveStatusActive : ""}`}><i className="fas fa-circle" /> {liveClass.status === "live" ? t("courses.live.statusLive") : t("courses.live.statusScheduled")}</span></div>
        <div className={styles.zoomMeetingTabs} role="tablist" aria-label={t("courses.live.meetingTabsAria")}>
          {zoomTabs.map((tab) => <button type="button" role="tab" aria-selected={activeTab === tab.id} className={activeTab === tab.id ? styles.zoomMeetingTabActive : ""} onClick={() => setActiveTab(tab.id)} key={tab.id}>{tab.id === "summary" && <i className="fas fa-sparkles" />}{t(tab.labelKey)}</button>)}
        </div>
        {activeTab === "upcoming" ? <div className={styles.zoomTableCard}>
          <div className={styles.zoomTableHeader}><span>{t("courses.live.table.startTime")}</span><span>{t("courses.live.table.topic")}</span><span>{t("courses.live.table.meetingId")}</span><span>{t("courses.live.table.actions")}</span></div>
          {liveClass.schedules.length ? liveClass.schedules.map((schedule) => <LiveScheduleRow key={schedule.schedule_id} schedule={schedule} topic={course?.name || t("courses.live.courseMeeting")} isTeacher={isTeacher} onOpen={(action) => navigate(`/courses/${courseId}/live?meetingId=${encodeURIComponent(schedule.meeting_id)}&action=${action}`)} />) : <div className={styles.zoomNoData}>{t("courses.live.noData")}</div>}
        </div> : <div className={styles.zoomNoDataPanel}><i className="fas fa-inbox" /><strong>{t("courses.live.noData")}</strong><span>{t("courses.live.noMeetingsHint")}</span></div>}
        {liveClass.provisioning_required && isTeacher && <button className="primary-action" type="button" disabled={provisionMutation.isPending} onClick={provision}><i className={`fas ${provisionMutation.isPending ? "fa-circle-notch fa-spin" : "fa-video"}`} />{provisionMutation.isPending ? t("courses.live.preparing") : t("courses.live.prepare")}</button>}
        {liveClass.provisioning_required && user?.role === "student" && <div className={styles.zoomNotice}><i className="fas fa-circle-info" /> {t("courses.live.teacherNotPrepared")}</div>}
        </div>
      </> : activeModule === "Assignments" ? <AssignmentsModule courseId={courseId} assignments={assignments} loading={assignmentsQuery.isLoading} error={assignmentsQuery.isError} isTeacher={isTeacher} onRefresh={() => assignmentsQuery.refetch().then(() => undefined)} onGrade={(id) => navigate(`/assignments/${id}/grading`)} /> : activeModule === "Discussions" ? <DiscussionModule courseId={courseId} /> : activeModule === "Participant" ? <ParticipantModule participants={participants} loading={participantsQuery.isLoading} error={participantsQuery.isError} isTeacher={isTeacher} currentUserId={user?.id} /> : materialKind ? <MaterialsModule courseId={courseId} kind={materialKind} chapters={materials} loading={materialsQuery.isLoading} error={materialsQuery.isError} selectedChapterId={selectedChapterId} onSelectChapter={setSelectedChapterId} onRefresh={() => materialsQuery.refetch().then(() => undefined)} isTeacher={isTeacher} /> : <div className={styles.courseModulePlaceholder}><p className="eyebrow">COURSE MODULE</p><h2>{moduleLabelKey ? t(moduleLabelKey) : activeModule}</h2><p>{t("courses.live.placeholderHint")}</p></div>}
    </div>
  </section>;
}

function LiveScheduleRow({ schedule, topic, isTeacher, onOpen }: { schedule: LiveClassSchedule; topic: string; isTeacher: boolean; onOpen: (action: "start" | "join") => void }) {
  const { t, formatDate } = useI18n();
  const timeLabel = schedule.next_start ? formatDate(schedule.next_start, { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : t("courses.live.nextClassTba");
  const action = schedule.can_start ? "start" : "join";
  const enabled = schedule.can_join || schedule.can_start;
  return <div className={styles.zoomTableRow}><span className={styles.zoomMeetingTime}>{timeLabel}<small>{formatWeekdayLabel(schedule.weekday, t)} · {schedule.start_time} – {schedule.end_time}</small></span><span className={styles.zoomMeetingTopic}>{topic}<small>{schedule.status === "unconfigured" ? t("courses.live.unconfigured") : schedule.status}</small></span><span className={styles.zoomMeetingId}>{schedule.meeting_number || "—"}</span><span><button className={enabled ? "primary-action" : "secondary-action"} type="button" disabled={!enabled} onClick={() => onOpen(action)}><i className={`fas ${isTeacher && action === "start" ? "fa-chalkboard-user" : "fa-arrow-right-to-bracket"}`} />{isTeacher && action === "start" ? t("courses.live.startClass") : enabled ? t("courses.live.joinClass") : t("courses.live.notOpen")}</button></span></div>;
}
