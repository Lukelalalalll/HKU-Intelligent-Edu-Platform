import React from "react";
import { useNavigate } from "react-router-dom";
import { type StudentDashboardData, type TeacherDashboardData } from "../../api";
import { useStudentDashboardQuery, useTeacherDashboardQuery } from "../../hooks/useDashboardQueries";
import { useAuth } from "../../store";
import WeeklyTimetable from "../../shared/components/WeeklyTimetable";

const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const formatDue = (value: string | null) => value ? new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "未设置截止时间";
const SCHEDULE_START_MINUTES = 8 * 60;
const SCHEDULE_DAYTIME_END = 20 * 60;
const SCHEDULE_END_MINUTES = 24 * 60;
const SCHEDULE_DAYTIME_PIXELS_PER_MINUTE = 1;
const SCHEDULE_EVENING_PIXELS_PER_MINUTE = 0.5;
const SCHEDULE_AXIS_HEIGHT = (SCHEDULE_DAYTIME_END - SCHEDULE_START_MINUTES) * SCHEDULE_DAYTIME_PIXELS_PER_MINUTE
  + (SCHEDULE_END_MINUTES - SCHEDULE_DAYTIME_END) * SCHEDULE_EVENING_PIXELS_PER_MINUTE;
const scheduleTicks = [8, 10, 12, 14, 16, 18, 20, 22, 24].map((hour) => hour * 60);
const minutesOf = (value: string) => {
  const [hours = 0, minutes = 0] = value.split(":").map(Number);
  const total = Number.isFinite(hours) && Number.isFinite(minutes) ? hours * 60 + minutes : 0;
  return Math.max(0, Math.min(SCHEDULE_END_MINUTES, total));
};
const scheduleAxisOffset = (minutes: number) => {
  const safeMinutes = Math.max(SCHEDULE_START_MINUTES, Math.min(SCHEDULE_END_MINUTES, minutes));
  if (safeMinutes <= SCHEDULE_DAYTIME_END) return (safeMinutes - SCHEDULE_START_MINUTES) * SCHEDULE_DAYTIME_PIXELS_PER_MINUTE;
  return (SCHEDULE_DAYTIME_END - SCHEDULE_START_MINUTES) * SCHEDULE_DAYTIME_PIXELS_PER_MINUTE
    + (safeMinutes - SCHEDULE_DAYTIME_END) * SCHEDULE_EVENING_PIXELS_PER_MINUTE;
};

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [weekOffset, setWeekOffset] = React.useState(0);
  const teacherQuery = useTeacherDashboardQuery(user?.role === "teacher");
  const data = teacherQuery.data ?? null;
  const error = teacherQuery.isError;
  if (user?.role === "student") return <StudentDashboard />;
  if (user?.role !== "teacher") return <div><div className="page-heading"><div><p className="eyebrow">{user?.role?.toUpperCase()} WORKSPACE</p><h1>你好，{user?.name}</h1><p className="muted">这是你的工作空间概览。</p></div></div><div className="welcome-panel"><h2>统一教学骨架已就绪</h2><p>课程、作业、文件和 AI 对话将在同一套角色感知的工作台中逐步展开。</p></div></div>;
  const base = new Date(); base.setDate(base.getDate() - ((base.getDay() + 6) % 7) + weekOffset * 7); base.setHours(0, 0, 0, 0);
  const weekLabel = `${base.toLocaleDateString("zh-CN", { month: "short", day: "numeric" })} – ${new Date(base.getTime() + 6 * 86400000).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}`;
  const schedule = data?.schedule ?? [];
  return <div className="teacher-dashboard">
    <div className="page-heading teacher-heading"><div><p className="eyebrow"><i className="fas fa-sparkles" /> TEACHER WORKSPACE</p><h1>你好，{user.name || user.username}</h1><p className="muted">今天也为学生创造有影响力的学习体验。</p></div><div className="date-chip"><i className="fas fa-calendar-day" /> {new Date().toLocaleDateString("zh-CN", { weekday: "long", month: "long", day: "numeric" })}</div></div>
    {error ? <div className="error-panel">暂时无法加载教学数据，请稍后重试。</div> : <div className="dashboard-grid">
      <section className="schedule-panel panel-card"><div className="panel-title"><div><p className="eyebrow">TIME SCHEDULE</p><h2>本周课程表</h2></div><div className="week-controls"><button onClick={() => setWeekOffset((v) => v - 1)} aria-label="上一周"><i className="fas fa-chevron-left" /></button><span>{weekLabel}</span><button onClick={() => setWeekOffset((v) => v + 1)} aria-label="下一周"><i className="fas fa-chevron-right" /></button><button className="today-button" onClick={() => setWeekOffset(0)}>本周</button></div></div><div className="timetable" style={{ "--schedule-axis-height": `${SCHEDULE_AXIS_HEIGHT}px` } as React.CSSProperties}><div className="time-column"><span className="time-title">时间</span>{scheduleTicks.map((minutes) => <span className={`time-tick ${minutes === SCHEDULE_START_MINUTES ? "time-tick-start" : ""}`} style={{ top: 48 + scheduleAxisOffset(minutes) }} key={minutes}>{minutes === SCHEDULE_END_MINUTES ? "24:00" : `${String(Math.floor(minutes / 60)).padStart(2, "0")}:00`}</span>)}</div>{weekdays.map((day, i) => <div className="day-column" key={day}><header><span>{day}</span><strong>{new Date(base.getTime() + i * 86400000).getDate()}</strong></header><div className="day-track">{scheduleTicks.slice(1).map((minutes) => <span className="schedule-grid-line" style={{ top: scheduleAxisOffset(minutes) }} aria-hidden="true" key={minutes} />)}{schedule.filter((s) => s.weekday === i + 1).map((item) => { const start = minutesOf(item.start_time); const end = Math.max(start, minutesOf(item.end_time)); const top = scheduleAxisOffset(start); const height = Math.max(52, scheduleAxisOffset(end) - top - 7); const compact = end - start <= 90 || height < 104; return <button className={`schedule-block ${compact ? "schedule-block-compact" : ""}`} style={{ top, height }} key={`${item.course_id}-${item.start_time}-${item.weekday}`} onClick={() => navigate(`/courses/${item.course_id}`)} aria-label={`${item.course_name}，${item.start_time} 至 ${item.end_time}，${item.room || "待定教室"}`}><strong>{item.course_code}</strong>{compact ? <small className="schedule-compact-details">{item.start_time} – {item.end_time} · {item.room || "待定教室"}</small> : <><span>{item.course_name}</span><small>{item.start_time} – {item.end_time}</small><small><i className="fas fa-location-dot" /> {item.room || "待定教室"}</small></>}</button>; })}{!schedule.some((s) => s.weekday === i + 1) && <span className="day-empty">—</span>}</div></div>)}</div></section>
      <aside className="dashboard-side"><section className="panel-card side-panel"><div className="panel-title"><div><p className="eyebrow">TODAY</p><h2>今日课程</h2></div><i className="fas fa-clock panel-icon" /></div>{schedule.filter((s) => s.weekday === ((new Date().getDay() + 6) % 7) + 1).map((item) => <button className="today-course" key={`${item.course_id}-${item.start_time}`} onClick={() => navigate(`/courses/${item.course_id}`)}><span className="time-label">{item.start_time}</span><div><strong>{item.course_name}</strong><span>{item.course_code} · {item.room || "待定教室"}</span></div><i className="fas fa-arrow-right" /></button>)}{!schedule.some((s) => s.weekday === ((new Date().getDay() + 6) % 7) + 1) && <div className="empty-state"><i className="fas fa-mug-hot" /><strong>今天没有课程</strong><span>享受一段专注时间吧。</span></div>}</section><section className="panel-card side-panel"><div className="panel-title"><div><p className="eyebrow">REVIEW QUEUE</p><h2>待批改作业</h2></div><i className="fas fa-file-pen panel-icon" /></div>{(data?.pending_assignments ?? []).map((item) => <button className="review-card" key={item.id} onClick={() => navigate(`/courses/${item.course_id}?module=Assignments`)}><span className="review-due">{formatDue(item.due_at)}</span><strong>{item.title}</strong><span>{item.course_name}</span><footer><small>待批改</small><b>{item.pending_count} 份</b></footer></button>)}{!data?.pending_assignments?.length && <div className="empty-state"><i className="fas fa-check-circle" /><strong>暂无待批改作业</strong><span>所有提交都已处理。</span></div>}</section></aside>
    </div>}
  </div>;
}

export function StudentDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [weekOffset, setWeekOffset] = React.useState(0);
  const studentQuery = useStudentDashboardQuery();
  const data = studentQuery.data ?? null;
  const error = studentQuery.isError;
  const schedule = data?.schedule ?? [];
  const today = ((new Date().getDay() + 6) % 7) + 1;
  const todaySchedule = schedule.filter((item) => item.weekday === today);
  const statusLabel: Record<StudentDashboardData["assignment_reminders"][number]["submission_status"], string> = { not_started: "待完成", submitted: "已提交", graded: "已评分", overdue: "已逾期" };
  return <div className="teacher-dashboard student-dashboard">
    <div className="page-heading teacher-heading"><div><p className="eyebrow"><i className="fas fa-sparkles" /> STUDENT WORKSPACE</p><h1>你好，{user?.name || user?.username}</h1><p className="muted">安排好每一节课，稳步完成你的学习计划。</p></div><div className="date-chip"><i className="fas fa-calendar-day" /> {new Date().toLocaleDateString("zh-CN", { weekday: "long", month: "long", day: "numeric" })}</div></div>
    {error ? <div className="error-panel">暂时无法加载学生数据，请稍后重试。</div> : <div className="dashboard-grid">
      <WeeklyTimetable items={schedule} weekOffset={weekOffset} onWeekOffsetChange={setWeekOffset} title="本周课表" />
      <aside className="dashboard-side"><section className="panel-card side-panel"><div className="panel-title"><div><p className="eyebrow">TODAY</p><h2>今日课程</h2></div><i className="fas fa-clock panel-icon" /></div>{todaySchedule.map((item) => <button className="today-course" key={`${item.course_id}-${item.start_time}`} onClick={() => navigate(`/courses/${item.course_id}`)}><span className="time-label">{item.start_time}</span><div><strong>{item.course_name}</strong><span>{item.course_code} · {item.room || "待定教室"}</span></div><i className="fas fa-arrow-right" /></button>)}{!todaySchedule.length && <div className="empty-state"><i className="fas fa-mug-hot" /><strong>今天没有课程</strong><span>享受一段专注时间吧。</span></div>}</section><section className="panel-card side-panel"><div className="panel-title"><div><p className="eyebrow">ASSIGNMENTS</p><h2>作业提醒</h2></div><i className="fas fa-file-pen panel-icon" /></div>{(data?.assignment_reminders ?? []).map((item) => <button className={`review-card assignment-reminder assignment-${item.submission_status}`} key={item.id} onClick={() => navigate(`/courses/${item.course_id}`)}><span className="review-due">{formatDue(item.due_at)}</span><strong>{item.title}</strong><span>{item.course_name}</span><footer><small>{statusLabel[item.submission_status]}</small><b>{item.score !== null ? `${item.score}/${item.max_score}` : "查看作业"}</b></footer></button>)}{!data?.assignment_reminders?.length && <div className="empty-state"><i className="fas fa-check-circle" /><strong>暂无作业提醒</strong><span>你已完成当前课程作业。</span></div>}</section></aside>
    </div>}
  </div>;
}

