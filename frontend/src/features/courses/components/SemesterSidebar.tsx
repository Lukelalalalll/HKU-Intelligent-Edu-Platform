import type { Course } from '../../../api';
import {
  COURSE_SEMESTERS,
  formatAcademicYear,
  formatDateRange,
  SEMESTER_LABELS,
  semesterDateRange,
  type CourseSemester,
} from '../courseTerms';
import styles from '../styles/CoursesRoute.module.css';

type Props = {
  courses: Course[];
  years: number[];
  selectedYear: number;
  selectedSemester: CourseSemester;
  currentYear: number;
  currentSemester: CourseSemester;
  onSelect: (year: number, semester: CourseSemester) => void;
};

export default function SemesterSidebar({ courses, years, selectedYear, selectedSemester, currentYear, currentSemester, onSelect }: Props) {
  const currentYears = years.filter((year) => year === currentYear);
  const previousYears = years.filter((year) => year !== currentYear);
  const renderYear = (year: number) => (
    <section className={`${styles.yearGroup} ${year === selectedYear ? styles.yearGroupActive : ''}`} key={year}>
      <div className={styles.yearHeader}>
        <div>
          <strong>{formatAcademicYear(year)}</strong>
          {year === currentYear && <span className={styles.currentBadge}>Current academic year</span>}
        </div>
        <span className={styles.yearCount}>{courses.filter((course) => course.academic_year_start === year).length}</span>
      </div>
      <div className={styles.semesterList}>
        {COURSE_SEMESTERS.map((semester) => {
          const isSelected = year === selectedYear && semester === selectedSemester;
          const isCurrent = year === currentYear && semester === currentSemester;
          const count = courses.filter((course) => course.academic_year_start === year && course.semester === semester).length;
          return (
            <button
              type="button"
              key={semester}
              className={`${styles.semesterButton} ${isSelected ? styles.semesterButtonActive : ''} ${isCurrent ? styles.semesterButtonCurrent : ''}`}
              aria-pressed={isSelected}
              onClick={() => onSelect(year, semester)}
            >
              <span>
                <b>{SEMESTER_LABELS[semester]}</b>
                <small>{formatDateRange(semesterDateRange(year, semester))}</small>
                {isCurrent && <em>Current</em>}
              </span>
              <strong>{count}</strong>
            </button>
          );
        })}
      </div>
    </section>
  );

  return (
    <aside className={styles.sidebar} aria-label="Academic year and semester">
      <div className={styles.sidebarIntro}>
        <span>ACADEMIC YEAR</span>
        <strong>Browse semesters</strong>
      </div>
      {currentYears.map(renderYear)}
      {previousYears.length > 0 && <p className={styles.previousLabel}>Previous academic years</p>}
      {previousYears.map(renderYear)}
    </aside>
  );
}

