import { apiFetch } from '@/shared/api/httpClient';
import { courseRequest, type CourseForm } from '@/features/courses/model/courseForm';
import type { Course, UnitSummary } from '@/shared/types/domain';

export const listCourses = () => apiFetch<Course[]>('/api/v1/cursos');

export const createCourse = (form: CourseForm) => apiFetch<Course>('/api/v1/cursos', { method: 'POST', json: courseRequest(form) });

export const updateCourse = (course: Course, form: CourseForm) =>
  apiFetch<Course>(`/api/v1/cursos/${encodeURIComponent(course.id)}`, { method: 'PUT', json: courseRequest(form, course) });

export const deleteCourse = (courseId: string) => apiFetch<void>(`/api/v1/cursos/${encodeURIComponent(courseId)}`, { method: 'DELETE' });

/** Recursos aprobados y por revisar de cada unidad del docente. */
export const listSummary = () => apiFetch<UnitSummary[]>('/api/v1/resumen');
