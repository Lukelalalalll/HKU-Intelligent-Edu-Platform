/**
 * Academic-year and semester helpers shared by the course pages.
 *
 * Semester ranges mirror the backend ``course_terms`` module so the UI and the
 * scheduling code agree on term boundaries.
 */
import type { Course, CourseSemester } from '../../api';
import { createTranslator, DEFAULT_LOCALE, formatDate, type Locale, type TranslationKey, type Translator } from '../../i18n';

export type { CourseSemester } from '../../api';

/**
 * Semester values in display order.
 */
export const COURSE_SEMESTERS: CourseSemester[] = ['semester_1', 'semester_2', 'summer'];

/**
 * Translation keys for each semester value; resolve them with ``t`` (or
 * {@link formatSemesterLabel}) so the label follows the active locale.
 */
export const SEMESTER_LABEL_KEYS: Record<CourseSemester, TranslationKey> = {
  semester_1: 'courses.semester.semester1',
  semester_2: 'courses.semester.semester2',
  summer: 'courses.semester.summer',
};

/** Default translator kept for non-React unit tests (source language). */
const defaultTranslator = createTranslator(DEFAULT_LOCALE);

/** Weekday translation keys indexed by ISO weekday (1 = Monday). */
const WEEKDAY_KEYS: TranslationKey[] = [
  'common.weekdays.mon',
  'common.weekdays.tue',
  'common.weekdays.wed',
  'common.weekdays.thu',
  'common.weekdays.fri',
  'common.weekdays.sat',
  'common.weekdays.sun',
];

/** Translate a semester value into a display label. */
export function formatSemesterLabel(semester: CourseSemester, t: Translator = defaultTranslator) {
  return t(SEMESTER_LABEL_KEYS[semester]);
}

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
 * Format a date range for the active locale.
 */
export function formatDateRange(range: { start: Date; end: Date }, locale: Locale = DEFAULT_LOCALE) {
  const options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' };
  return `${formatDate(locale, range.start, options)} – ${formatDate(locale, range.end, options)}`;
}

/** Translate an ISO weekday, falling back to the raw number for bad data. */
export function formatWeekdayLabel(weekday: number, t: Translator = defaultTranslator) {
  const key = WEEKDAY_KEYS[weekday - 1];
  return key ? t(key) : String(weekday);
}

/**
 * Join distinct room names, falling back to a placeholder.
 *
 * The list separator follows the locale: English uses a comma, Chinese uses
 * the enumeration comma.
 */
export function formatCourseLocations(schedules: Course['schedules'], t: Translator = defaultTranslator, locale: Locale = DEFAULT_LOCALE) {
  const separator = locale === 'en' ? ', ' : '、';
  const locations = [...new Set(schedules.map((schedule) => schedule.room.trim()).filter(Boolean))];
  return locations.length ? locations.join(separator) : t('common.roomTba');
}

/**
 * Render weekly meeting times as one line per schedule.
 */
export function formatCourseTimes(schedules: Course['schedules'], t: Translator = defaultTranslator) {
  if (!schedules.length) return t('courses.common.tbd');
  return schedules.map((schedule) => `${formatWeekdayLabel(schedule.weekday, t)} ${schedule.start_time}–${schedule.end_time}`).join('\n');
}
