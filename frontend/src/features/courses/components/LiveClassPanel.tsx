import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { courseMaterialsApi, liveClassApi, participantApi, type Course, type CourseChapter, type CourseMaterial, type LiveClass, type LiveClassSchedule, type MaterialKind, type Participant } from "../../../api";
import { useAuth } from "../../../store";
import { SEMESTER_LABELS } from "../courseTerms";
import styles from "../styles/CoursesRoute.module.css";

const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const formatTime = (value: string | null) => value ? new Intl.DateTimeFormat("zh-CN", { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "暂无下一课次";
const sidebarItems = ["Announcements", "Assignments", "Discussions", "Grades", "Participant", "Syllabus", "Lecture Files", "Tutorial File", "Zoom", "Panopto Recordings"];
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
  const [materials, setMaterials] = useState<CourseChapter[]>([]);
  const [materialsLoading, setMaterialsLoading] = useState(false);
  const [materialsError, setMaterialsError] = useState(false);
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);

  const load = useCallback(() => liveClassApi.get(courseId).then((response) => setLiveClass(response.data)).catch(() => undefined).finally(() => setLoading(false)), [courseId]);
  useEffect(() => { load(); const timer = window.setInterval(load, 30000); return () => window.clearInterval(timer); }, [load]);
  useEffect(() => {
    if (activeModule !== "Participant") return;
    setParticipantsLoading(true);
    setParticipantsError(false);
    participantApi.list(courseId).then((response) => setParticipants(response.data)).catch(() => setParticipantsError(true)).finally(() => setParticipantsLoading(false));
  }, [activeModule, courseId]);
  const materialKind: MaterialKind | null = activeModule === "Lecture Files" ? "lecture" : activeModule === "Tutorial File" ? "tutorial" : null;
  useEffect(() => {
    if (!materialKind) return;
    setMaterialsLoading(true);
    setMaterialsError(false);
    courseMaterialsApi.list(courseId, materialKind).then((response) => {
      setMaterials(response.data);
      setSelectedChapterId((current) => response.data.some((chapter) => chapter.id === current) ? current : response.data[0]?.id || null);
    }).catch(() => setMaterialsError(true)).finally(() => setMaterialsLoading(false));
  }, [courseId, materialKind]);

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
        {sidebarItems.map((item) => <a href="#" key={item} className={activeModule === item ? styles.zoomCourseNavActive : ""} aria-current={activeModule === item ? "page" : undefined} onClick={(event) => { event.preventDefault(); setActiveModule(item); }}><i className={`fas ${item === "Zoom" ? "fa-video" : item === "Participant" ? "fa-user-group" : item.includes("File") ? "fa-folder-open" : "fa-circle-dot"}`} />{item}</a>)}
      </nav>
    </aside>
    <div className={`${styles.zoomMain} ${activeModule === "Zoom" ? styles.zoomMainZoom : styles.zoomMainHku} ${activeModule === "Participant" ? styles.zoomMainParticipant : ""} ${materialKind ? styles.zoomMainMaterials : ""}`}>
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
      </> : activeModule === "Participant" ? <ParticipantModule participants={participants} loading={participantsLoading} error={participantsError} isTeacher={isTeacher} currentUserId={user?.id} /> : materialKind ? <MaterialsModule courseId={courseId} kind={materialKind} chapters={materials} loading={materialsLoading} error={materialsError} selectedChapterId={selectedChapterId} onSelectChapter={setSelectedChapterId} onRefresh={() => courseMaterialsApi.list(courseId, materialKind).then((response) => { setMaterials(response.data); setSelectedChapterId((current) => response.data.some((chapter) => chapter.id === current) ? current : response.data[0]?.id || null); })} isTeacher={isTeacher} /> : <div className={styles.courseModulePlaceholder}><p className="eyebrow">COURSE MODULE</p><h2>{activeModule}</h2><p>这是课程导航预留的 HKU 工作区。选择左侧 Zoom 后可查看实时课堂和会议安排。</p></div>}
    </div>
  </section>;
}

function ParticipantModule({ participants, loading, error, isTeacher, currentUserId }: { participants: Participant[]; loading: boolean; error: boolean; isTeacher: boolean; currentUserId?: string }) {
  return <div className={styles.participantContent}>
    <header className={styles.participantHeading}><div><p className="eyebrow">COURSE PARTICIPANTS</p><h2>Participant</h2><span>{participants.length} 名学生</span></div><i className="fas fa-user-group" /></header>
    {loading ? <div className={styles.participantState}><i className="fas fa-circle-notch fa-spin" /><strong>正在加载学生名单…</strong></div> : error ? <div className={styles.participantState}><i className="fas fa-circle-exclamation" /><strong>暂时无法加载学生名单</strong><span>请稍后重试。</span></div> : !participants.length ? <div className={styles.participantState}><i className="fas fa-users-slash" /><strong>暂无学生</strong><span>该课程还没有选课学生。</span></div> : <div className={styles.participantGrid}>{participants.map((participant) => <ParticipantCard key={participant.id} participant={participant} detailed={isTeacher} current={participant.id === currentUserId} />)}</div>}
  </div>;
}

function MaterialsModule({ courseId, kind, chapters, loading, error, selectedChapterId, onSelectChapter, onRefresh, isTeacher }: { courseId: string; kind: MaterialKind; chapters: CourseChapter[]; loading: boolean; error: boolean; selectedChapterId: string | null; onSelectChapter: (id: string) => void; onRefresh: () => Promise<any>; isTeacher: boolean }) {
  const [busy, setBusy] = useState(false);
  const selectedChapter = chapters.find((chapter) => chapter.id === selectedChapterId) || null;
  const label = kind === "lecture" ? "Lecture Files" : "Tutorial File";

  const createChapter = async () => {
    const title = window.prompt("请输入 chapter 名称", `Chapter ${chapters.length + 1}`)?.trim();
    if (!title) return;
    setBusy(true);
    try { await courseMaterialsApi.createChapter(courseId, { kind, title }); await onRefresh(); toast.success("Chapter 已创建"); }
    catch (error: any) { toast.error(error.response?.data?.detail || "创建 chapter 失败"); }
    finally { setBusy(false); }
  };

  const renameChapter = async (chapter: CourseChapter) => {
    const title = window.prompt("重命名 chapter", chapter.title)?.trim();
    if (!title || title === chapter.title) return;
    setBusy(true);
    try { await courseMaterialsApi.updateChapter(courseId, chapter.id, { title }); await onRefresh(); toast.success("Chapter 已更新"); }
    catch (error: any) { toast.error(error.response?.data?.detail || "更新 chapter 失败"); }
    finally { setBusy(false); }
  };

  const moveChapter = async (chapter: CourseChapter, offset: number) => {
    const index = chapters.findIndex((item) => item.id === chapter.id);
    const next = index + offset;
    if (next < 0 || next >= chapters.length) return;
    setBusy(true);
    try { await courseMaterialsApi.updateChapter(courseId, chapter.id, { sort_order: next }); await onRefresh(); }
    catch (error: any) { toast.error(error.response?.data?.detail || "调整 chapter 顺序失败"); }
    finally { setBusy(false); }
  };

  const deleteChapter = async (chapter: CourseChapter) => {
    if (!window.confirm(`确认删除“${chapter.title}”及其中的全部文件吗？`)) return;
    setBusy(true);
    try { await courseMaterialsApi.deleteChapter(courseId, chapter.id); await onRefresh(); toast.success("Chapter 已删除"); }
    catch (error: any) { toast.error(error.response?.data?.detail || "删除 chapter 失败"); }
    finally { setBusy(false); }
  };

  const uploadFiles = async (files: FileList | null) => {
    if (!selectedChapter || !files?.length) return;
    setBusy(true);
    try { for (const file of Array.from(files)) await courseMaterialsApi.upload(courseId, selectedChapter.id, file); await onRefresh(); toast.success("资料已上传"); }
    catch (error: any) { toast.error(error.response?.data?.detail || "资料上传失败"); }
    finally { setBusy(false); }
  };

  const deleteMaterial = async (material: CourseMaterial) => {
    if (!window.confirm(`确认删除“${material.title}”吗？`)) return;
    setBusy(true);
    try { await courseMaterialsApi.delete(courseId, material.id); await onRefresh(); toast.success("资料已删除"); }
    catch (error: any) { toast.error(error.response?.data?.detail || "删除资料失败"); }
    finally { setBusy(false); }
  };

  return <div className={styles.materialsContent}>
    <header className={styles.materialsHeading}><div><p className="eyebrow">COURSE MATERIALS</p><h2>{label}</h2><span>{chapters.length} 个 chapter · {chapters.reduce((total, chapter) => total + chapter.material_count, 0)} 个文件</span></div><i className="fas fa-folder-open" /></header>
    {loading ? <div className={styles.materialsState}><i className="fas fa-circle-notch fa-spin" /><strong>正在加载课程资料…</strong></div> : error ? <div className={styles.materialsState}><i className="fas fa-circle-exclamation" /><strong>暂时无法加载课程资料</strong><span>请稍后重试。</span></div> : <div className={styles.materialsWorkspace}>
      <aside className={styles.chapterPanel}><div className={styles.chapterPanelHeader}><div><span>CHAPTERS</span><strong>章节目录</strong></div>{isTeacher && <button type="button" className="primary-action" onClick={() => void createChapter()} disabled={busy}><i className="fas fa-plus" /> 新建</button>}</div>
        {!chapters.length ? <div className={styles.chapterEmpty}><i className="fas fa-list" /><span>{isTeacher ? "先创建一个 chapter" : "暂无章节"}</span></div> : <div className={styles.chapterList}>{chapters.map((chapter, index) => <div key={chapter.id} className={`${styles.chapterItem} ${chapter.id === selectedChapterId ? styles.chapterItemActive : ""}`}><button type="button" onClick={() => onSelectChapter(chapter.id)}><span className={styles.chapterIndex}>{String(index + 1).padStart(2, "0")}</span><span><strong>{chapter.title}</strong><small>{chapter.material_count} 个文件</small></span></button>{isTeacher && <div className={styles.chapterActions}><button type="button" title="上移" disabled={busy || index === 0} onClick={() => void moveChapter(chapter, -1)}><i className="fas fa-chevron-up" /></button><button type="button" title="下移" disabled={busy || index === chapters.length - 1} onClick={() => void moveChapter(chapter, 1)}><i className="fas fa-chevron-down" /></button><button type="button" title="重命名" disabled={busy} onClick={() => void renameChapter(chapter)}><i className="fas fa-pen" /></button><button type="button" title="删除" disabled={busy} onClick={() => void deleteChapter(chapter)}><i className="fas fa-trash" /></button></div>}</div>)}</div>}
      </aside>
      <main className={styles.materialsMain}>{selectedChapter ? <><div className={styles.chapterTitleRow}><div><p className="eyebrow">CHAPTER {String(chapters.indexOf(selectedChapter) + 1).padStart(2, "0")}</p><h3>{selectedChapter.title}</h3><span>{selectedChapter.material_count} 个资料</span></div>{isTeacher && <label className="primary-action"><i className="fas fa-upload" /> 上传资料<input type="file" multiple hidden onChange={(event) => { void uploadFiles(event.target.files); event.currentTarget.value = ""; }} /></label>}</div>{selectedChapter.materials.length ? <div className={styles.materialGrid}>{selectedChapter.materials.map((material) => <MaterialCard key={material.id} courseId={courseId} material={material} isTeacher={isTeacher} busy={busy} onDelete={() => void deleteMaterial(material)} />)}</div> : <div className={styles.materialsState}><i className="fas fa-file-circle-plus" /><strong>{isTeacher ? "这个 chapter 还没有资料" : "这个 chapter 暂无资料"}</strong><span>{isTeacher ? "上传讲义、阅读材料或其他课程文件。" : "教师上传资料后会显示在这里。"}</span>{isTeacher && <label className="secondary-action"><i className="fas fa-upload" /> 上传第一份资料<input type="file" multiple hidden onChange={(event) => { void uploadFiles(event.target.files); event.currentTarget.value = ""; }} /></label>}</div>}</> : <div className={styles.materialsState}><i className="fas fa-folder-open" /><strong>{isTeacher ? "开始整理课程资料" : "暂无课程资料"}</strong><span>{isTeacher ? "创建 chapter 后即可上传文件。" : "教师还没有发布资料。"}</span>{isTeacher && <button type="button" className="primary-action" onClick={() => void createChapter()} disabled={busy}><i className="fas fa-plus" /> 新建 chapter</button>}</div>}</main>
    </div>}
  </div>;
}

function MaterialCard({ courseId, material, isTeacher, busy, onDelete }: { courseId: string; material: CourseMaterial; isTeacher: boolean; busy: boolean; onDelete: () => void }) {
  const download = async () => {
    try {
      const response = await courseMaterialsApi.download(courseId, material.id);
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = material.file_name; anchor.click(); URL.revokeObjectURL(url);
    } catch (error: any) { toast.error(error.response?.data?.detail || "文件下载失败"); }
  };
  return <article className={styles.materialCard}><div className={styles.materialIcon}><i className={`fas ${material.mime_type.includes("pdf") ? "fa-file-pdf" : material.mime_type.startsWith("image/") ? "fa-file-image" : "fa-file-lines"}`} /></div><div className={styles.materialInfo}><strong title={material.title}>{material.title}</strong><span>{material.file_name}</span><small>{formatBytes(material.size_bytes)} · {new Date(material.uploaded_at).toLocaleDateString("zh-CN")}</small></div><div className={styles.materialActions}><button type="button" className="secondary-action" onClick={() => void download()}><i className="fas fa-download" /> 下载</button>{isTeacher && <button type="button" className={styles.iconAction} title="删除" disabled={busy} onClick={onDelete}><i className="fas fa-trash" /></button>}</div></article>;
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
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
