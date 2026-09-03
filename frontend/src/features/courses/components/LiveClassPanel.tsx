import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { liveClassApi, participantApi, type Course, type LiveClass, type LiveClassSchedule, type Participant } from "../../../api";
import { useAuth } from "../../../store";
import { SEMESTER_LABELS } from "../courseTerms";
import styles from "../styles/CoursesRoute.module.css";

const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const formatTime = (value: string | null) => value ? new Intl.DateTimeFormat("zh-CN", { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "暂无下一课次";
const sidebarItems = ["Home", "Announcements", "Files", "Assignments", "Discussions", "Grades", "Participant", "Syllabus", "Library Resources", "Zoom", "Panopto Recordings"];
const zoomTabs = [
  { id: "upcoming", label: "Upcoming Meetings" },
  { id: "previous", label: "Previous Meetings" },
  { id: "recordings", label: "Cloud Recordings" },
  { id: "summary", label: "Meeting Summary" },
] as const;

export default function LiveClassPanel({ courseId, course }: { courseId: string; course?: Course }) {
  const user = useAuth((state) => state.user);
  const navigate = useNavigate();
  const [liveClass, setLiveClass] = useState<LiveClass | null>(null);
  const [loading, setLoading] = useState(true);
  const [provisioning, setProvisioning] = useState(false);
  const [activeTab, setActiveTab] = useState<(typeof zoomTabs)[number]["id"]>("upcoming");
  const [activeModule, setActiveModule] = useState("Zoom");
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [participantsLoading, setParticipantsLoading] = useState(false);
  const [participantsError, setParticipantsError] = useState(false);

  const load = useCallback(() => liveClassApi.get(courseId).then((response) => setLiveClass(response.data)).catch(() => undefined).finally(() => setLoading(false)), [courseId]);
  useEffect(() => { load(); const timer = window.setInterval(load, 30000); return () => window.clearInterval(timer); }, [load]);
  useEffect(() => {
    if (activeModule !== "Participant") return;
    setParticipantsLoading(true);
    setParticipantsError(false);
    participantApi.list(courseId).then((response) => setParticipants(response.data)).catch(() => setParticipantsError(true)).finally(() => setParticipantsLoading(false));
  }, [activeModule, courseId]);

  const provision = async () => {
    setProvisioning(true);
    try { const response = await liveClassApi.provision(courseId); setLiveClass(response.data); toast.success("课堂会议已准备"); }
    catch (error: any) { toast.error(error.response?.data?.detail || "Zoom 会议准备失败"); }
    finally { setProvisioning(false); }
  };

  if (loading) return <section className={styles.zoomState}><i className="fas fa-circle-notch fa-spin" /><strong>正在检查 Zoom 课堂状态…</strong></section>;
  if (!liveClass) return <section className={styles.zoomState}><i className="fas fa-circle-exclamation" /><strong>暂时无法加载课堂状态</strong><span>请稍后重试。</span></section>;
  const isTeacher = user?.role === "teacher" || user?.role === "admin";
  const termLabel = course ? `${course.academic_year_start}/${String(course.academic_year_start + 1).slice(-2)} · ${SEMESTER_LABELS[course.semester]}` : "Course workspace";
  return <section className={styles.zoomWorkspace} aria-label="Zoom 课程工作区">
    <aside className={styles.zoomSidebar}>
      <div className={styles.zoomSidebarBrand}><span className={styles.zoomSidebarMenu}><i className="fas fa-bars" /></span><div><strong>{course?.code || "COURSE"}</strong><small>{course?.name || "Zoom workspace"}</small></div></div>
      <div className={styles.zoomSidebarTerm}>{termLabel}</div>
      <nav className={styles.zoomCourseNav} aria-label="课程导航">
        {sidebarItems.map((item) => <a href="#" key={item} className={activeModule === item ? styles.zoomCourseNavActive : ""} aria-current={activeModule === item ? "page" : undefined} onClick={(event) => { event.preventDefault(); setActiveModule(item); }}><i className={`fas ${item === "Zoom" ? "fa-video" : item === "Home" ? "fa-house" : item === "Participant" ? "fa-user-group" : "fa-circle-dot"}`} />{item}</a>)}
      </nav>
    </aside>
    <div className={`${styles.zoomMain} ${activeModule === "Zoom" ? styles.zoomMainZoom : styles.zoomMainHku} ${activeModule === "Participant" ? styles.zoomMainParticipant : ""}`}>
      {activeModule === "Zoom" ? <>
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
        {liveClass.provisioning_required && isTeacher && <button className="primary-action" type="button" disabled={provisioning} onClick={provision}><i className={`fas ${provisioning ? "fa-circle-notch fa-spin" : "fa-video"}`} />{provisioning ? "准备中…" : "准备 Zoom 课堂"}</button>}
        {liveClass.provisioning_required && user?.role === "student" && <div className={styles.zoomNotice}><i className="fas fa-circle-info" /> 教师尚未准备 Zoom 课堂，准备完成后即可加入。</div>}
        </div>
      </> : activeModule === "Participant" ? <ParticipantModule participants={participants} loading={participantsLoading} error={participantsError} isTeacher={isTeacher} currentUserId={user?.id} /> : <div className={styles.courseModulePlaceholder}><p className="eyebrow">COURSE MODULE</p><h2>{activeModule}</h2><p>这是课程导航预留的 HKU 工作区。选择左侧 Zoom 后可查看实时课堂和会议安排。</p></div>}
    </div>
  </section>;
}

function ParticipantModule({ participants, loading, error, isTeacher, currentUserId }: { participants: Participant[]; loading: boolean; error: boolean; isTeacher: boolean; currentUserId?: string }) {
  return <div className={styles.participantContent}>
    <header className={styles.participantHeading}><div><p className="eyebrow">COURSE PARTICIPANTS</p><h2>Participant</h2><span>{participants.length} 名学生</span></div><i className="fas fa-user-group" /></header>
    {loading ? <div className={styles.participantState}><i className="fas fa-circle-notch fa-spin" /><strong>正在加载学生名单…</strong></div> : error ? <div className={styles.participantState}><i className="fas fa-circle-exclamation" /><strong>暂时无法加载学生名单</strong><span>请稍后重试。</span></div> : !participants.length ? <div className={styles.participantState}><i className="fas fa-users-slash" /><strong>暂无学生</strong><span>该课程还没有选课学生。</span></div> : <div className={styles.participantGrid}>{participants.map((participant) => <ParticipantCard key={participant.id} participant={participant} detailed={isTeacher} current={participant.id === currentUserId} />)}</div>}
  </div>;
}

function ParticipantCard({ participant, detailed, current }: { participant: Participant; detailed: boolean; current: boolean }) {
  const initials = (participant.name || participant.username || participant.email).slice(0, 1).toUpperCase();
  return <article className={`${styles.participantCard} ${current ? styles.participantCardCurrent : ""}`}>
    <div className={styles.participantIdentity}>{detailed && (participant.avatar_url ? <img className={styles.participantAvatar} src={participant.avatar_url} alt="" /> : <span className={styles.participantAvatar}>{initials}</span>)}<div><strong>{participant.name || participant.email}</strong>{current && <small className={styles.participantCurrentLabel}>你</small>}</div></div>
    <div className={styles.participantDetails}><span><i className="fas fa-envelope" />{participant.email}</span>{detailed && <><span><i className="fas fa-at" />{participant.username}</span>{participant.enrolled_at && <span><i className="fas fa-calendar-plus" />加入于 {new Date(participant.enrolled_at).toLocaleDateString("zh-CN")}</span>}</>}</div>
  </article>;
}

function LiveScheduleRow({ schedule, topic, isTeacher, onOpen }: { schedule: LiveClassSchedule; topic: string; isTeacher: boolean; onOpen: (action: "start" | "join") => void }) {
  const action = schedule.can_start ? "start" : "join";
  const enabled = schedule.can_join || schedule.can_start;
  return <div className={styles.zoomTableRow}><span className={styles.zoomMeetingTime}>{formatTime(schedule.next_start)}<small>{weekdays[schedule.weekday - 1] || `周${schedule.weekday}`} · {schedule.start_time} – {schedule.end_time}</small></span><span className={styles.zoomMeetingTopic}>{topic}<small>{schedule.status === "unconfigured" ? "未配置" : schedule.status}</small></span><span className={styles.zoomMeetingId}>{schedule.meeting_number || "—"}</span><span><button className={enabled ? "primary-action" : "secondary-action"} type="button" disabled={!enabled} onClick={() => onOpen(action)}><i className={`fas ${isTeacher && action === "start" ? "fa-chalkboard-user" : "fa-arrow-right-to-bracket"}`} />{isTeacher && action === "start" ? "开始课堂" : enabled ? "加入课堂" : "未开放"}</button></span></div>;
}
