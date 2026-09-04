import type { Course, CourseSemester } from '../../api';

export type { CourseSemester } from '../../api';

export const COURSE_SEMESTERS: CourseSemester[] = ['semester_1', 'semester_2', 'summer'];

export const SEMESTER_LABELS: Record<CourseSemester, string> = {
  semester_1: 'Semester 1',
  semester_2: 'Semester 2',
  summer: 'Summer Semester',
};

export function academicYearStartFor(date: Date) {
  return date.getMonth() >= 8 ? date.getFullYear() : date.getFullYear() - 1;
}

export function semesterFor(date: Date): CourseSemester {
  const month = date.getMonth() + 1;
  if (month >= 9 && month <= 12) return 'semester_1';
  if (month >= 2 && month <= 5) return 'semester_2';
  if (month >= 6 && month <= 8) return 'summer';
  return 'semester_2';
}

export function semesterDateRange(year: number, semester: CourseSemester) {
  const nextYear = year + 1;
  if (semester === 'semester_1') return { start: new Date(year, 8, 1), end: new Date(year, 11, 31) };
  if (semester === 'semester_2') return { start: new Date(nextYear, 1, 1), end: new Date(nextYear, 4, 31) };
  return { start: new Date(nextYear, 5, 1), end: new Date(nextYear, 7, 31) };
}

export function formatAcademicYear(year: number) {
  return `${year}-${String(year + 1).slice(-2)}`;
}

export function getAcademicYears(courses: Course[], currentDate = new Date()) {
  return [...new Set([academicYearStartFor(currentDate), ...courses.map((course) => course.academic_year_start)])]
    .sort((left, right) => right - left);
}

export function formatDateRange(range: { start: Date; end: Date }) {
  const formatter = new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', year: 'numeric' });
  return `${formatter.format(range.start)} – ${formatter.format(range.end)}`;
}

export function formatCourseLocations(schedules: Course['schedules']) {
  const locations = [...new Set(schedules.map((schedule) => schedule.room.trim()).filter(Boolean))];
  return locations.length ? locations.join('、') : '待定教室';
}

export function formatCourseTimes(schedules: Course['schedules']) {
  if (!schedules.length) return '待定';
  const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  return schedules.map((schedule) => `${weekdays[schedule.weekday - 1] || `周${schedule.weekday}`} ${schedule.start_time}–${schedule.end_time}`).join('\n');
}
