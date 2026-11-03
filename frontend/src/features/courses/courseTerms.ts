/**
 * Academic-year and semester helpers shared by the course pages.
 *
 * Semester ranges mirror the backend ``course_terms`` module so the UI and the
 * scheduling code agree on term boundaries.
 */
import type { Course, CourseSemester } from '../../api';

export type { CourseSemester } from '../../api';

/**
 * Semester values in display order.
 */
export const COURSE_SEMESTERS: CourseSemester[] = ['semester_1', 'semester_2', 'summer'];

/**
 * Human labels for each semester value.
 */
export const SEMESTER_LABELS: Record<CourseSemester, string> = {
  semester_1: 'Semester 1',
  semester_2: 'Semester 2',
  summer: 'Summer Semester',
};

/**
 * Return the academic year that starts in September for a date.
 */
export function academicYearStartFor(date: Date) {
  return date.getMonth() >= 8 ? date.getFullYear() : date.getFullYear() - 1;
}

/**
 * Map a date to its teaching semester; January maps to semester 2.
 */
export function semesterFor(date: Date): CourseSemester {
  const month = date.getMonth() + 1;
  if (month >= 9 && month <= 12) return 'semester_1';
  if (month >= 2 && month <= 5) return 'semester_2';
  if (month >= 6 && month <= 8) return 'summer';
  return 'semester_2';
}

/**
 * Return the first and last day of a semester.
 */
export function semesterDateRange(year: number, semester: CourseSemester) {
  const nextYear = year + 1;
  if (semester === 'semester_1') return { start: new Date(year, 8, 1), end: new Date(year, 11, 31) };
  if (semester === 'semester_2') return { start: new Date(nextYear, 1, 1), end: new Date(nextYear, 4, 31) };
  return { start: new Date(nextYear, 5, 1), end: new Date(nextYear, 7, 31) };
}

/**
 * Format an academic year as ``2025-26``.
 */
export function formatAcademicYear(year: number) {
  return `${year}-${String(year + 1).slice(-2)}`;
}

/**
 * List the academic years that have courses, newest first.
 */
export function getAcademicYears(courses: Course[], currentDate = new Date()) {
  return [...new Set([academicYearStartFor(currentDate), ...courses.map((course) => course.academic_year_start)])]
    .sort((left, right) => right - left);
}

/**
 * Format a date range for the Chinese UI.
 */
export function formatDateRange(range: { start: Date; end: Date }) {
  const formatter = new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', year: 'numeric' });
  return `${formatter.format(range.start)} – ${formatter.format(range.end)}`;
}

/**
 * Join distinct room names, falling back to a placeholder.
 */
export function formatCourseLocations(schedules: Course['schedules']) {
  const locations = [...new Set(schedules.map((schedule) => schedule.room.trim()).filter(Boolean))];
  return locations.length ? locations.join('、') : '待定教室';
}

/**
 * Render weekly meeting times as one line per schedule.
 */
export function formatCourseTimes(schedules: Course['schedules']) {
  if (!schedules.length) return '待定';
  const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  return schedules.map((schedule) => `${weekdays[schedule.weekday - 1] || `周${schedule.weekday}`} ${schedule.start_time}–${schedule.end_time}`).join('\n');
}
