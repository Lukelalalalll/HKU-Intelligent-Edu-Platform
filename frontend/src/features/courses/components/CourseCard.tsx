import { Link } from 'react-router-dom';
import type { Course } from '../../../api';
import { useI18n } from '../../../i18n';
import { formatDateRange, formatSemesterLabel, semesterDateRange } from '../courseTerms';
import styles from '../styles/CoursesRoute.module.css';

/**
 * Course summary card linking to the course detail route.
 */
export default function CourseCard({ course }: { course: Course }) {
  const { t, locale } = useI18n();
  return (
    <Link to={`/courses/${course.id}`} className={styles.courseCard}>
      <div className={styles.courseTop}>
        <span className={styles.courseCode}>{course.code}</span>
        <span className={styles.semesterPill}>{formatSemesterLabel(course.semester, t)}</span>
      </div>
      <h2>{course.name}</h2>
      <p>{course.description || t('courses.card.noDescription')}</p>
      <div className={styles.courseMeta}>
        <span>{t('courses.card.teacher')}<strong>{course.teacher_name}</strong></span>
        <span>{t('courses.card.students')}<strong>{t(course.enrolled_count === 1 ? 'courses.card.enrolledCount.one' : 'courses.card.enrolledCount.other', { count: course.enrolled_count })}</strong></span>
      </div>
      <footer>
        <span>{formatDateRange(semesterDateRange(course.academic_year_start, course.semester), locale)}</span>
        <strong>{t('courses.card.viewCourse')} <i className="fas fa-arrow-right" aria-hidden="true" /></strong>
      </footer>
    </Link>
  );
}
