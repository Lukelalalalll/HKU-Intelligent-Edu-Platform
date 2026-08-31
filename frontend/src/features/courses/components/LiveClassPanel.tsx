import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { liveClassApi, type LiveClass, type LiveClassSchedule } from "../../../api";
import { useAuth } from "../../../store";
import styles from "../styles/CoursesRoute.module.css";

const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const formatTime = (value: string | null) => value ? new Intl.DateTimeFormat("zh-CN", { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "暂无下一课次";

export default function LiveClassPanel({ courseId }: { courseId: string }) {
  const user = useAuth((state) => state.user);
  const navigate = useNavigate();
  const [liveClass, setLiveClass] = useState<LiveClass | null>(null);
  const [loading, setLoading] = useState(true);
  const [provisioning, setProvisioning] = useState(false);

  const load = useCallback(() => liveClassApi.get(courseId).then((response) => setLiveClass(response.data)).catch(() => undefined).finally(() => setLoading(false)), [courseId]);
  useEffect(() => { load(); const timer = window.setInterval(load, 30000); return () => window.clearInterval(timer); }, [load]);

  const provision = async () => {
    setProvisioning(true);
    try { const response = await liveClassApi.provision(courseId); setLiveClass(response.data); toast.success("课堂会议已准备"); }
    catch (error: any) { toast.error(error.response?.data?.detail || "Zoom 会议准备失败"); }
    finally { setProvisioning(false); }
  };

  if (loading) return <section className={styles.detailSection}><p className="eyebrow">LIVE CLASS</p><h2>实时课堂</h2><div className={styles.emptyInline}>正在检查课堂状态…</div></section>;
  if (!liveClass) return <section className={styles.detailSection}><p className="eyebrow">LIVE CLASS</p><h2>实时课堂</h2><div className={styles.emptyInline}>暂时无法加载课堂状态，请稍后重试。</div></section>;
  return <section className={`${styles.detailSection} ${styles.livePanel}`}>
    <div className={styles.liveHeader}><div><p className="eyebrow">LIVE CLASS</p><h2>Zoom 实时课堂</h2><span>教师：{liveClass.teacher_name} · {liveClass.timezone}</span></div><span className={`${styles.liveStatus} ${liveClass.status === "live" ? styles.liveStatusActive : ""}`}><i className="fas fa-circle" /> {liveClass.status === "live" ? "进行中" : "按课表开放"}</span></div>
    {liveClass.schedules.map((schedule) => <LiveScheduleRow key={schedule.schedule_id} courseId={courseId} schedule={schedule} isTeacher={user?.role === "teacher" || user?.role === "admin"} onOpen={(action) => navigate(`/courses/${courseId}/live?meetingId=${encodeURIComponent(schedule.meeting_id)}&action=${action}`)} />)}
    {liveClass.provisioning_required && (user?.role === "teacher" || user?.role === "admin") && <button className="primary-action" type="button" disabled={provisioning} onClick={provision}><i className={`fas ${provisioning ? "fa-circle-notch fa-spin" : "fa-video"}`} />{provisioning ? "准备中…" : "准备 Zoom 课堂"}</button>}
    {liveClass.provisioning_required && user?.role === "student" && <div className={styles.emptyInline}>教师尚未准备 Zoom 课堂，准备完成后即可加入。</div>}
  </section>;
}

function LiveScheduleRow({ courseId, schedule, isTeacher, onOpen }: { courseId: string; schedule: LiveClassSchedule; isTeacher: boolean; onOpen: (action: "start" | "join") => void }) {
  const action = schedule.can_start ? "start" : "join";
  const enabled = schedule.can_join || schedule.can_start;
  return <div className={styles.liveRow}><div><strong>{weekdays[schedule.weekday - 1] || `周${schedule.weekday}`} {schedule.start_time} – {schedule.end_time}</strong><small>下一次：{formatTime(schedule.next_start)} · {schedule.status === "unconfigured" ? "未配置" : schedule.status}</small></div><button className={enabled ? "primary-action" : "secondary-action"} type="button" disabled={!enabled} onClick={() => onOpen(action)}><i className={`fas ${isTeacher && action === "start" ? "fa-chalkboard-user" : "fa-arrow-right-to-bracket"}`} />{isTeacher && action === "start" ? "开始课堂" : enabled ? "加入课堂" : "未开放"}</button></div>;
}
