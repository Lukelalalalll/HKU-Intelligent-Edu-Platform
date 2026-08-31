import React, { useEffect, useMemo } from 'react';
import { useAuth } from '../../../store';
import { api, type Course } from '../../../api';
import SemesterSidebar from '../components/SemesterSidebar';
import CourseGrid from '../components/CourseGrid';
import {
  academicYearStartFor,
  formatAcademicYear,
  getAcademicYears,
  SEMESTER_LABELS,
  semesterFor,
  type CourseSemester,
} from '../courseTerms';
import styles from '../styles/CoursesRoute.module.css';

export default function CoursesRoute() {
  const { user } = useAuth();
  const [courses, setCourses] = React.useState<Course[]>([]);
  const [currentDate, setCurrentDate] = React.useState(() => new Date());
  const [selectedYear, setSelectedYear] = React.useState(() => academicYearStartFor(new Date()));
  const [selectedSemester, setSelectedSemester] = React.useState<CourseSemester>(() => semesterFor(new Date()));
  const [query, setQuery] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);

  useEffect(() => {
    api.get<Course[]>('/courses').then((response) => setCourses(response.data)).catch(() => setError(true)).finally(() => setLoading(false));
  }, []);

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
        <div><p className="eyebrow">ACADEMIC</p><h1>{user?.role === 'teacher' ? '我的课程' : '课程'}</h1><p className="muted">按 academic year 和 semester 浏览你的课程记录。</p></div>
      </header>
      <div className={styles.layout}>
        <SemesterSidebar courses={courses} years={years} selectedYear={selectedYear} selectedSemester={selectedSemester} currentYear={currentYear} currentSemester={currentSemester} onSelect={selectTerm} />
        <main className={styles.main}>
          <div className={styles.toolbar}>
            <div><h2>{query.trim() ? '搜索结果' : `${formatAcademicYear(selectedYear)} · ${SEMESTER_LABELS[selectedSemester]}`}</h2><span>{selectedCourses.length} 门课程</span></div>
            <label className={styles.search}><i className="fas fa-search" aria-hidden="true" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索课程、代码或教师" aria-label="搜索课程、代码或教师" /></label>
          </div>
          {loading && <div className={styles.state}><i className="fas fa-circle-notch fa-spin" />正在加载课程…</div>}
          {error && <div className={styles.state}><i className="fas fa-circle-exclamation" />暂时无法加载课程，请稍后重试。</div>}
          {!loading && !error && <CourseGrid courses={selectedCourses} searching={Boolean(query.trim())} />}
        </main>
      </div>
    </div>
  );
}

