import React, { useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, type Assignment, type Course } from '../../../api';
import { formatDateRange, SEMESTER_LABELS, semesterDateRange } from '../courseTerms';
import styles from '../styles/CoursesRoute.module.css';
import LiveClassPanel from '../components/LiveClassPanel';

const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const formatDue = (value: string | null) => value ? new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '未设置截止时间';

export default function CourseDetailRoute() {
  const { courseId } = useParams();
  const [course, setCourse] = React.useState<Course | null>(null);
  const [assignments, setAssignments] = React.useState<Assignment[]>([]);
  useEffect(() => {
    if (!courseId) return;
    api.get<Course>(`/courses/${courseId}`).then((response) => setCourse(response.data)).catch(() => undefined);
    api.get<Assignment[]>(`/courses/${courseId}/assignments`).then((response) => setAssignments(response.data)).catch(() => undefined);
  }, [courseId]);
  if (!course) return <div className="loading-screen">正在加载课程…</div>;
  return <div className={styles.detail}><Link className={styles.back} to="/courses"><i className="fas fa-arrow-left" /> 返回我的课程</Link><section className={styles.detailHero}><div><span className={styles.courseCode}>{course.code}</span><h1>{course.name}</h1><p>{course.description || '暂无课程简介'}</p><small>{formatAcademicLabel(course)}</small></div><div><strong>{course.enrolled_count}</strong><span>名学生</span></div></section><LiveClassPanel courseId={course.id} /><div className={styles.detailGrid}><section className={styles.detailSection}><p className="eyebrow">SCHEDULE</p><h2>上课安排</h2>{course.schedules.length ? course.schedules.map((schedule) => <div className={styles.scheduleRow} key={`${schedule.weekday}-${schedule.start_time}`}><b>{weekdays[schedule.weekday - 1] || `周${schedule.weekday}`}</b><span>{schedule.start_time} – {schedule.end_time}</span><span><i className="fas fa-location-dot" /> {schedule.room || '待定教室'}</span></div>) : <div className={styles.emptyInline}>暂无排课信息</div>}</section><section className={styles.detailSection}><p className="eyebrow">COURSEWORK</p><h2>作业概览</h2>{assignments.length ? assignments.map((assignment) => <Link className={styles.assignmentRow} to={`/assignments/${assignment.id}/grading`} key={assignment.id}><span><strong>{assignment.title}</strong><small>{assignment.description || '暂无说明'}</small></span><b>{formatDue(assignment.due_at)}</b></Link>) : <div className={styles.emptyInline}>暂无作业，后续可在此管理。</div>}</section></div></div>;
}

function formatAcademicLabel(course: Course) {
  return `${course.academic_year_start}-${String(course.academic_year_start + 1).slice(-2)} · ${SEMESTER_LABELS[course.semester]} · ${formatDateRange(semesterDateRange(course.academic_year_start, course.semester))}`;
}
