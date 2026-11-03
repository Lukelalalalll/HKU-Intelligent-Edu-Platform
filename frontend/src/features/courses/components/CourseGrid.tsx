import type { Course } from '../../../api';
import { useI18n } from '../../../i18n';
import CourseCard from './CourseCard';
import styles from '../styles/CoursesRoute.module.css';

/**
 * Course card grid with a search-aware empty state.
 */
export default function CourseGrid({ courses, searching }: { courses: Course[]; searching: boolean }) {
  const { t } = useI18n();
  if (!courses.length) {
    return (
      <div className={styles.emptyState}>
        <i className={`fas ${searching ? 'fa-magnifying-glass' : 'fa-book-open'}`} aria-hidden="true" />
        <strong>{searching ? t('courses.grid.noMatchTitle') : t('courses.grid.emptyTitle')}</strong>
        <span>{searching ? t('courses.grid.noMatchHint') : t('courses.grid.emptyHint')}</span>
      </div>
    );
  }
  return <div className={styles.courseGrid}>{courses.map((course) => <CourseCard key={course.id} course={course} />)}</div>;
}
