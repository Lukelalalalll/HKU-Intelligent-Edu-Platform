import React from "react";
import { useNavigate } from "react-router-dom";
import { type StudentDashboardData, type TeacherDashboardData } from "../../api";
import { useStudentDashboardQuery, useTeacherDashboardQuery } from "../../hooks/useDashboardQueries";
import { useI18n, type I18nValue, type TranslationKey } from "../../i18n";
import { useAuth } from "../../store";
import WeeklyTimetable from "../../shared/components/WeeklyTimetable";

const weekdayKeys: TranslationKey[] = ["common.weekdays.mon", "common.weekdays.tue", "common.weekdays.wed", "common.weekdays.thu", "common.weekdays.fri", "common.weekdays.sat", "common.weekdays.sun"];
const formatDue = (value: string | null, formatDate: I18nValue["formatDate"], fallback: string) => value ? formatDate(new Date(value), { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : fallback;
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

function DashboardSidePanel({ eyebrow, title, icon, children }: { eyebrow: string; title: string; icon: string; children: React.ReactNode }) {
  return <section className="panel-card side-panel"><div className="panel-title"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div><i className={`fas ${icon} panel-icon`} /></div><div className="side-panel-body" tabIndex={0}>{children}</div></section>;
}

export function Dashboard() {
  const { user } = useAuth();
  const { t, formatDate } = useI18n();
  const navigate = useNavigate();
  const [weekOffset, setWeekOffset] = React.useState(0);
  const teacherQuery = useTeacherDashboardQuery(user?.role === "teacher");
  const data = teacherQuery.data ?? null;
  const error = teacherQuery.isError;
  if (user?.role === "student") return <StudentDashboard />;
  if (user?.role !== "teacher") return <div><div className="page-heading"><div><p className="eyebrow">{user?.role?.toUpperCase()} WORKSPACE</p><h1>{t("dashboard.greeting", { name: user?.name ?? "" })}</h1><p className="muted">{t("dashboard.welcome.subtitle")}</p></div></div><div className="welcome-panel"><h2>{t("dashboard.welcome.title")}</h2><p>{t("dashboard.welcome.body")}</p></div></div>;
  const base = new Date(); base.setDate(base.getDate() - ((base.getDay() + 6) % 7) + weekOffset * 7); base.setHours(0, 0, 0, 0);
  const weekLabel = `${formatDate(base, { month: "short", day: "numeric" })} – ${formatDate(new Date(base.getTime() + 6 * 86400000), { month: "short", day: "numeric" })}`;
  const schedule = data?.schedule ?? [];
  return <div className="teacher-dashboard">
    <div className="page-heading teacher-heading"><div><p className="eyebrow"><i className="fas fa-sparkles" /> TEACHER WORKSPACE</p><h1>{t("dashboard.greeting", { name: user.name || user.username })}</h1><p className="muted">{t("dashboard.teacher.subtitle")}</p></div><div className="date-chip"><i className="fas fa-calendar-day" /> {formatDate(new Date(), { weekday: "long", month: "long", day: "numeric" })}</div></div>
    {error ? <div className="error-panel">{t("dashboard.teacher.error")}</div> : <div className="dashboard-grid">
      <section className="schedule-panel panel-card"><div className="panel-title"><div><p className="eyebrow">TIME SCHEDULE</p><h2>{t("dashboard.teacher.scheduleTitle")}</h2></div><div className="week-controls"><button onClick={() => setWeekOffset((v) => v - 1)} aria-label={t("dashboard.timetable.previousWeek")}><i className="fas fa-chevron-left" /></button><span>{weekLabel}</span><button onClick={() => setWeekOffset((v) => v + 1)} aria-label={t("dashboard.timetable.nextWeek")}><i className="fas fa-chevron-right" /></button><button className="today-button" onClick={() => setWeekOffset(0)}>{t("dashboard.timetable.thisWeek")}</button></div></div><div className="timetable" style={{ "--schedule-axis-height": `${SCHEDULE_AXIS_HEIGHT}px` } as React.CSSProperties}><div className="time-column"><span className="time-title">{t("dashboard.timetable.timeColumn")}</span>{scheduleTicks.map((minutes) => <span className={`time-tick ${minutes === SCHEDULE_START_MINUTES ? "time-tick-start" : ""}`} style={{ top: 48 + scheduleAxisOffset(minutes) }} key={minutes}>{minutes === SCHEDULE_END_MINUTES ? "24:00" : `${String(Math.floor(minutes / 60)).padStart(2, "0")}:00`}</span>)}</div>{weekdayKeys.map((day, i) => <div className="day-column" key={day}><header><span>{t(day)}</span><strong>{new Date(base.getTime() + i * 86400000).getDate()}</strong></header><div className="day-track">{scheduleTicks.slice(1).map((minutes) => <span className="schedule-grid-line" style={{ top: scheduleAxisOffset(minutes) }} aria-hidden="true" key={minutes} />)}{schedule.filter((s) => s.weekday === i + 1).map((item) => { const start = minutesOf(item.start_time); const end = Math.max(start, minutesOf(item.end_time)); const top = scheduleAxisOffset(start); const height = Math.max(52, scheduleAxisOffset(end) - top - 7); const compact = end - start <= 90 || height < 104; return <button className={`schedule-block ${compact ? "schedule-block-compact" : ""}`} style={{ top, height }} key={`${item.course_id}-${item.start_time}-${item.weekday}`} onClick={() => navigate(`/courses/${item.course_id}`)} aria-label={t("dashboard.timetable.slotAria", { course: item.course_name, start: item.start_time, end: item.end_time, room: item.room || t("common.roomTba") })}><strong>{item.course_code}</strong>{compact ? <small className="schedule-compact-details">{item.start_time} – {item.end_time} · {item.room || t("common.roomTba")}</small> : <><span>{item.course_name}</span><small>{item.start_time} – {item.end_time}</small><small><i className="fas fa-location-dot" /> {item.room || t("common.roomTba")}</small></>}</button>; })}{!schedule.some((s) => s.weekday === i + 1) && <span className="day-empty">—</span>}</div></div>)}</div></section>
      <aside className="dashboard-side">
        <DashboardSidePanel eyebrow="TODAY" title={t("dashboard.today.title")} icon="fa-clock">
          {schedule.filter((s) => s.weekday === ((new Date().getDay() + 6) % 7) + 1).map((item) => <button className="today-course" key={`${item.course_id}-${item.start_time}`} onClick={() => navigate(`/courses/${item.course_id}`)}><span className="time-label">{item.start_time}</span><div><strong>{item.course_name}</strong><span>{item.course_code} · {item.room || t("common.roomTba")}</span></div><i className="fas fa-arrow-right" /></button>)}
          {!schedule.some((s) => s.weekday === ((new Date().getDay() + 6) % 7) + 1) && <div className="empty-state"><i className="fas fa-mug-hot" /><strong>{t("dashboard.today.emptyTitle")}</strong><span>{t("dashboard.today.emptyBody")}</span></div>}
        </DashboardSidePanel>
        <DashboardSidePanel eyebrow="REVIEW QUEUE" title={t("dashboard.teacher.reviewTitle")} icon="fa-file-pen">
          {(data?.pending_assignments ?? []).map((item) => <button className="review-card" key={item.id} onClick={() => navigate(`/courses/${item.course_id}?module=Assignments`)}><span className="review-due">{formatDue(item.due_at, formatDate, t("dashboard.dueUnset"))}</span><strong>{item.title}</strong><span>{item.course_name}</span><footer><small>{t("dashboard.teacher.pendingLabel")}</small><b>{t("dashboard.teacher.pendingCount", { count: item.pending_count ?? 0 })}</b></footer></button>)}
          {!data?.pending_assignments?.length && <div className="empty-state"><i className="fas fa-check-circle" /><strong>{t("dashboard.teacher.reviewEmptyTitle")}</strong><span>{t("dashboard.teacher.reviewEmptyBody")}</span></div>}
        </DashboardSidePanel>
      </aside>
    </div>}
  </div>;
}

export function StudentDashboard() {
  const { user } = useAuth();
  const { t, formatDate } = useI18n();
  const navigate = useNavigate();
  const [weekOffset, setWeekOffset] = React.useState(0);
  const studentQuery = useStudentDashboardQuery();
  const data = studentQuery.data ?? null;
  const error = studentQuery.isError;
  const schedule = data?.schedule ?? [];
  const today = ((new Date().getDay() + 6) % 7) + 1;
  const todaySchedule = schedule.filter((item) => item.weekday === today);
  const statusLabel: Record<StudentDashboardData["assignment_reminders"][number]["submission_status"], TranslationKey> = { not_started: "dashboard.status.notStarted", submitted: "dashboard.status.submitted", graded: "dashboard.status.graded", overdue: "dashboard.status.overdue" };
  return <div className="teacher-dashboard student-dashboard">
    <div className="page-heading teacher-heading"><div><p className="eyebrow"><i className="fas fa-sparkles" /> STUDENT WORKSPACE</p><h1>{t("dashboard.greeting", { name: user?.name || user?.username || "" })}</h1><p className="muted">{t("dashboard.student.subtitle")}</p></div><div className="date-chip"><i className="fas fa-calendar-day" /> {formatDate(new Date(), { weekday: "long", month: "long", day: "numeric" })}</div></div>
    {error ? <div className="error-panel">{t("dashboard.student.error")}</div> : <div className="dashboard-grid">
      <WeeklyTimetable items={schedule} weekOffset={weekOffset} onWeekOffsetChange={setWeekOffset} title={t("dashboard.student.timetableTitle")} />
      <aside className="dashboard-side">
        <DashboardSidePanel eyebrow="TODAY" title={t("dashboard.today.title")} icon="fa-clock">
          {todaySchedule.map((item) => <button className="today-course" key={`${item.course_id}-${item.start_time}`} onClick={() => navigate(`/courses/${item.course_id}`)}><span className="time-label">{item.start_time}</span><div><strong>{item.course_name}</strong><span>{item.course_code} · {item.room || t("common.roomTba")}</span></div><i className="fas fa-arrow-right" /></button>)}
          {!todaySchedule.length && <div className="empty-state"><i className="fas fa-mug-hot" /><strong>{t("dashboard.today.emptyTitle")}</strong><span>{t("dashboard.today.emptyBody")}</span></div>}
        </DashboardSidePanel>
        <DashboardSidePanel eyebrow="ASSIGNMENTS" title={t("dashboard.student.assignmentsTitle")} icon="fa-file-pen">
          {(data?.assignment_reminders ?? []).map((item) => <button className={`review-card assignment-reminder assignment-${item.submission_status}`} key={item.id} onClick={() => navigate(`/courses/${item.course_id}`)}><span className="review-due">{formatDue(item.due_at, formatDate, t("dashboard.dueUnset"))}</span><strong>{item.title}</strong><span>{item.course_name}</span><footer><small>{t(statusLabel[item.submission_status])}</small><b>{item.score !== null ? `${item.score}/${item.max_score}` : t("dashboard.student.viewAssignment")}</b></footer></button>)}
          {!data?.assignment_reminders?.length && <div className="empty-state"><i className="fas fa-check-circle" /><strong>{t("dashboard.student.assignmentsEmptyTitle")}</strong><span>{t("dashboard.student.assignmentsEmptyBody")}</span></div>}
        </DashboardSidePanel>
      </aside>
    </div>}
  </div>;
}

