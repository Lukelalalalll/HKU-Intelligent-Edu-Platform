import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api, type Course } from '../../../api';
import { formatCourseLocations, formatCourseTimes, formatDateRange, SEMESTER_LABELS, semesterDateRange } from '../courseTerms';
import styles from '../styles/CoursesRoute.module.css';
import LiveClassPanel from '../components/LiveClassPanel';

export default function CourseDetailRoute() {
  const { courseId } = useParams();
  const [course, setCourse] = React.useState<Course | null>(null);
  useEffect(() => {
    if (!courseId) return;
    api.get<Course>(`/courses/${courseId}`).then((response) => setCourse(response.data)).catch(() => undefined);
  }, [courseId]);
  if (!course) return <div className="loading-screen">正在加载课程…</div>;
  return <div className={`${styles.detail} course-detail-page`}><section className={styles.detailHero}><div className={`${styles.detailHeroPanel} ${styles.detailHeroMain} shared-welcome-banner`}><div className="shared-welcome-banner-content"><span className={styles.courseCode}>{course.code}</span><h1>{course.name}</h1><p>{course.description || '暂无课程简介'}</p><small>{formatAcademicLabel(course)}</small></div></div><div className={`${styles.detailHeroPanel} ${styles.detailHeroAside}`}><div className={styles.detailStat}><span className={styles.detailStatLabel}><i className="fas fa-location-dot" /> 课程地点</span><strong>{formatCourseLocations(course.schedules)}</strong></div><div className={styles.detailStat}><span className={styles.detailStatLabel}><i className="fas fa-user-group" /> 学生数量</span><strong>{course.enrolled_count}</strong><small>名学生</small></div><div className={styles.detailStat}><span className={styles.detailStatLabel}><i className="fas fa-calendar-days" /> 上课时间</span><strong className={styles.detailScheduleValue}>{formatCourseTimes(course.schedules)}</strong></div></div></section><LiveClassPanel courseId={course.id} course={course} /></div>;
}

function formatAcademicLabel(course: Course) {
  return `${course.academic_year_start}-${String(course.academic_year_start + 1).slice(-2)} · ${SEMESTER_LABELS[course.semester]} · ${formatDateRange(semesterDateRange(course.academic_year_start, course.semester))}`;
}
