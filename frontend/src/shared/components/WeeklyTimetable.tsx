import React from "react";
import { useNavigate } from "react-router-dom";
import { useI18n, type TranslationKey } from "../../i18n";

/**
 * One weekly schedule entry plotted on the timetable grid.
 */
export type TimetableItem = {
  course_id: string;
  course_code: string;
  course_name: string;
  weekday: number;
  start_time: string;
  end_time: string;
  room: string;
  teacher_name?: string;
};

const weekdayKeys: TranslationKey[] = ["common.weekdays.mon", "common.weekdays.tue", "common.weekdays.wed", "common.weekdays.thu", "common.weekdays.fri", "common.weekdays.sat", "common.weekdays.sun"];
const SCHEDULE_START_MINUTES = 8 * 60;
const SCHEDULE_DAYTIME_END = 20 * 60;
const SCHEDULE_END_MINUTES = 24 * 60;
const SCHEDULE_AXIS_HEIGHT = (SCHEDULE_DAYTIME_END - SCHEDULE_START_MINUTES) + (SCHEDULE_END_MINUTES - SCHEDULE_DAYTIME_END) * 0.5;
const scheduleTicks = [8, 10, 12, 14, 16, 18, 20, 22, 24].map((hour) => hour * 60);

const minutesOf = (value: string) => {
  const [hours = 0, minutes = 0] = value.split(":").map(Number);
  const total = Number.isFinite(hours) && Number.isFinite(minutes) ? hours * 60 + minutes : 0;
  return Math.max(0, Math.min(SCHEDULE_END_MINUTES, total));
};

const scheduleAxisOffset = (minutes: number) => {
  const safeMinutes = Math.max(SCHEDULE_START_MINUTES, Math.min(SCHEDULE_END_MINUTES, minutes));
  if (safeMinutes <= SCHEDULE_DAYTIME_END) return safeMinutes - SCHEDULE_START_MINUTES;
  return (SCHEDULE_DAYTIME_END - SCHEDULE_START_MINUTES) + (safeMinutes - SCHEDULE_DAYTIME_END) * 0.5;
};

/**
 * Week grid that plots schedule items and navigates to course detail.
 */
export default function WeeklyTimetable({ items, weekOffset, onWeekOffsetChange, title }: { items: TimetableItem[]; weekOffset: number; onWeekOffsetChange: (offset: number) => void; title?: string }) {
  const navigate = useNavigate();
  const { t, formatDate } = useI18n();
  const base = new Date();
  base.setDate(base.getDate() - ((base.getDay() + 6) % 7) + weekOffset * 7);
  base.setHours(0, 0, 0, 0);
  const weekLabel = `${formatDate(base, { month: "short", day: "numeric" })} – ${formatDate(new Date(base.getTime() + 6 * 86400000), { month: "short", day: "numeric" })}`;

  return <section className="schedule-panel panel-card">
    <div className="panel-title"><div><p className="eyebrow">TIME SCHEDULE</p><h2>{title ?? t("dashboard.timetable.defaultTitle")}</h2></div><div className="week-controls"><button onClick={() => onWeekOffsetChange(weekOffset - 1)} aria-label={t("dashboard.timetable.previousWeek")}><i className="fas fa-chevron-left" /></button><span>{weekLabel}</span><button onClick={() => onWeekOffsetChange(weekOffset + 1)} aria-label={t("dashboard.timetable.nextWeek")}><i className="fas fa-chevron-right" /></button><button className="today-button" onClick={() => onWeekOffsetChange(0)}>{t("dashboard.timetable.thisWeek")}</button></div></div>
    <div className="timetable" style={{ "--schedule-axis-height": `${SCHEDULE_AXIS_HEIGHT}px` } as React.CSSProperties}>
      <div className="time-column"><span className="time-title">{t("dashboard.timetable.timeColumn")}</span>{scheduleTicks.map((minutes) => <span className={`time-tick ${minutes === SCHEDULE_START_MINUTES ? "time-tick-start" : ""}`} style={{ top: 48 + scheduleAxisOffset(minutes) }} key={minutes}>{minutes === SCHEDULE_END_MINUTES ? "24:00" : `${String(Math.floor(minutes / 60)).padStart(2, "0")}:00`}</span>)}</div>
      {weekdayKeys.map((day, index) => <div className="day-column" key={day}><header><span>{t(day)}</span><strong>{new Date(base.getTime() + index * 86400000).getDate()}</strong></header><div className="day-track">{scheduleTicks.slice(1).map((minutes) => <span className="schedule-grid-line" style={{ top: scheduleAxisOffset(minutes) }} aria-hidden="true" key={minutes} />)}{items.filter((item) => item.weekday === index + 1).map((item) => { const start = minutesOf(item.start_time); const end = Math.max(start, minutesOf(item.end_time)); const top = scheduleAxisOffset(start); const height = Math.max(52, scheduleAxisOffset(end) - top - 7); const compact = end - start <= 90 || height < 104; return <button className={`schedule-block ${compact ? "schedule-block-compact" : ""}`} style={{ top, height }} key={`${item.course_id}-${item.start_time}-${item.weekday}`} onClick={() => navigate(`/courses/${item.course_id}`)} aria-label={t("dashboard.timetable.slotAria", { course: item.course_name, start: item.start_time, end: item.end_time, room: item.room || t("common.roomTba") })}><strong>{item.course_code}</strong>{compact ? <small className="schedule-compact-details">{item.start_time} – {item.end_time} · {item.room || t("common.roomTba")}</small> : <><span>{item.course_name}</span><small>{item.start_time} – {item.end_time}</small><small><i className="fas fa-location-dot" /> {item.room || t("common.roomTba")}</small></>}</button>; })}{!items.some((item) => item.weekday === index + 1) && <span className="day-empty">—</span>}</div></div>)}
    </div>
  </section>;
}
