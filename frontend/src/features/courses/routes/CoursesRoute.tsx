import React, { useEffect, useMemo } from 'react';
import { useAuth } from '../../../store';
import { useI18n } from '../../../i18n';
import { useCoursesQuery } from '../../../hooks/useCourseQueries';
import SemesterSidebar from '../components/SemesterSidebar';
import CourseGrid from '../components/CourseGrid';
import {
  academicYearStartFor,
  formatAcademicYear,
  formatSemesterLabel,
  getAcademicYears,
  semesterFor,
  type CourseSemester,
} from '../courseTerms';
import styles from '../styles/CoursesRoute.module.css';

/**
 * Course browser: term picker, search and the course grid.
 */
export default function CoursesRoute() {
  const { user } = useAuth();
  const { t } = useI18n();
  const coursesQuery = useCoursesQuery();
  const courses = coursesQuery.data ?? [];
  const [currentDate, setCurrentDate] = React.useState(() => new Date());
  const [selectedYear, setSelectedYear] = React.useState(() => academicYearStartFor(new Date()));
  const [selectedSemester, setSelectedSemester] = React.useState<CourseSemester>(() => semesterFor(new Date()));
  const [query, setQuery] = React.useState('');
  const loading = coursesQuery.isLoading;
  const error = coursesQuery.isError;

  useEffect(() => {
    const tomorrow = new Date(currentDate);
    tomorrow.setHours(24, 0, 0, 0);
    const timeout = window.setTimeout(() => setCurrentDate(new Date()), Math.max(1, tomorrow.getTime() - Date.now()));
    return () => window.clearTimeout(timeout);
  }, [currentDate]);

  const currentYear = academicYearStartFor(currentDate);
  const currentSemester = semesterFor(currentDate);
  const years = useMemo(() => getAcademicYears(courses, currentDate), [courses, currentDate]);
  const selectedCourses = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    if (normalized) return courses.filter((course) => [course.code, course.name, course.teacher_name].some((value) => value.toLocaleLowerCase().includes(normalized)));
    return courses.filter((course) => course.academic_year_start === selectedYear && course.semester === selectedSemester);
  }, [courses, query, selectedSemester, selectedYear]);

  useEffect(() => {
    if (!years.includes(selectedYear)) setSelectedYear(years[0] ?? currentYear);
  }, [currentYear, selectedYear, years]);

  const selectTerm = (year: number, semester: CourseSemester) => {
    setSelectedYear(year);
    setSelectedSemester(semester);
    setQuery('');
  };

  return (
    <div className={styles.page}>
      <header className={styles.pageHeading}>
        <div><p className="eyebrow">ACADEMIC</p><h1>{t(user?.role === 'teacher' ? 'common.nav.myCourses' : 'common.nav.courses')}</h1><p className="muted">{t('courses.route.subtitle')}</p></div>
      </header>
      <div className={styles.layout}>
        <SemesterSidebar courses={courses} years={years} selectedYear={selectedYear} selectedSemester={selectedSemester} currentYear={currentYear} currentSemester={currentSemester} onSelect={selectTerm} />
        <main className={styles.main}>
          <div className={styles.toolbar}>
            <div><h2>{query.trim() ? t('courses.route.searchResults') : `${formatAcademicYear(selectedYear)} · ${formatSemesterLabel(selectedSemester, t)}`}</h2><span>{t(selectedCourses.length === 1 ? 'courses.route.courseCount.one' : 'courses.route.courseCount.other', { count: selectedCourses.length })}</span></div>
            <label className={styles.search}><i className="fas fa-search" aria-hidden="true" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('courses.route.searchPlaceholder')} aria-label={t('courses.route.searchPlaceholder')} /></label>
          </div>
          {loading && <div className={styles.state}><i className="fas fa-circle-notch fa-spin" />{t('courses.route.loading')}</div>}
          {error && <div className={styles.state}><i className="fas fa-circle-exclamation" />{t('courses.route.loadError')}</div>}
          {!loading && !error && <CourseGrid courses={selectedCourses} searching={Boolean(query.trim())} />}
        </main>
      </div>
    </div>
  );
}
