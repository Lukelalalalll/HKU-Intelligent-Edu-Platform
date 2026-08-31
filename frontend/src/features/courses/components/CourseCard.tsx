import { Link } from 'react-router-dom';
import type { Course } from '../../../api';
import { formatDateRange, SEMESTER_LABELS, semesterDateRange } from '../courseTerms';
import styles from '../styles/CoursesRoute.module.css';

export default function CourseCard({ course }: { course: Course }) {
  return (
    <Link to={`/courses/${course.id}`} className={styles.courseCard}>
      <div className={styles.courseTop}>
        <span className={styles.courseCode}>{course.code}</span>
        <span className={styles.semesterPill}>{SEMESTER_LABELS[course.semester]}</span>
      </div>
      <h2>{course.name}</h2>
      <p>{course.description || '暂无课程简介'}</p>
      <div className={styles.courseMeta}>
        <span>教师<strong>{course.teacher_name}</strong></span>
        <span>学生<strong>{course.enrolled_count} 名</strong></span>
      </div>
      <footer>
        <span>{formatDateRange(semesterDateRange(course.academic_year_start, course.semester))}</span>
        <strong>查看课程 <i className="fas fa-arrow-right" aria-hidden="true" /></strong>
      </footer>
    </Link>
  );
}

