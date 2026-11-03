import React from 'react';
import { useParams } from 'react-router-dom';
import { useCourseQuery } from '../../../hooks/useCourseQueries';
import { useI18n, type Locale, type Translator } from '../../../i18n';
import type { Course } from '../../../api';
import { formatCourseLocations, formatCourseTimes, formatDateRange, formatSemesterLabel, semesterDateRange } from '../courseTerms';
import styles from '../styles/CoursesRoute.module.css';
import LiveClassPanel from '../components/LiveClassPanel';

/**
 * Course detail hero with the live-class workspace.
 */
export default function CourseDetailRoute() {
  const { courseId } = useParams();
  const { t, locale } = useI18n();
  const courseQuery = useCourseQuery(courseId);
  const course = courseQuery.data;
  if (!course) return <div className="loading-screen">{t('courses.common.loadingCourse')}</div>;
  return <div className={`${styles.detail} course-detail-page`}><section className={styles.detailHero}><div className={`${styles.detailHeroPanel} ${styles.detailHeroMain} shared-welcome-banner`}><div className="shared-welcome-banner-content"><span className={styles.courseCode}>{course.code}</span><h1>{course.name}</h1><p>{course.description || t('courses.card.noDescription')}</p><small>{formatAcademicLabel(course, t, locale)}</small></div></div><div className={`${styles.detailHeroPanel} ${styles.detailHeroAside}`}><div className={styles.detailStat}><span className={styles.detailStatLabel}><i className="fas fa-location-dot" /> {t('courses.detail.location')}</span><strong>{formatCourseLocations(course.schedules, t, locale)}</strong></div><div className={styles.detailStat}><span className={styles.detailStatLabel}><i className="fas fa-user-group" /> {t('courses.detail.studentCount')}</span><strong>{course.enrolled_count}</strong><small>{t(course.enrolled_count === 1 ? 'courses.detail.enrolledUnit.one' : 'courses.detail.enrolledUnit.other')}</small></div><div className={styles.detailStat}><span className={styles.detailStatLabel}><i className="fas fa-calendar-days" /> {t('courses.detail.schedule')}</span><strong className={styles.detailScheduleValue}>{formatCourseTimes(course.schedules, t)}</strong></div></div></section><LiveClassPanel courseId={course.id} course={course} /></div>;
}

function formatAcademicLabel(course: Course, t: Translator, locale: Locale) {
  return `${course.academic_year_start}-${String(course.academic_year_start + 1).slice(-2)} · ${formatSemesterLabel(course.semester, t)} · ${formatDateRange(semesterDateRange(course.academic_year_start, course.semester), locale)}`;
}
