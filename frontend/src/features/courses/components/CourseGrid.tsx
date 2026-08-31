import type { Course } from '../../../api';
import CourseCard from './CourseCard';
import styles from '../styles/CoursesRoute.module.css';

export default function CourseGrid({ courses, searching }: { courses: Course[]; searching: boolean }) {
  if (!courses.length) {
    return (
      <div className={styles.emptyState}>
        <i className={`fas ${searching ? 'fa-magnifying-glass' : 'fa-book-open'}`} aria-hidden="true" />
        <strong>{searching ? '没有匹配的课程' : '这个 semester 暂无课程'}</strong>
        <span>{searching ? '尝试搜索其他课程代码、名称或教师。' : '选择其他 semester 查看课程记录。'}</span>
      </div>
    );
  }
  return <div className={styles.courseGrid}>{courses.map((course) => <CourseCard key={course.id} course={course} />)}</div>;
}

