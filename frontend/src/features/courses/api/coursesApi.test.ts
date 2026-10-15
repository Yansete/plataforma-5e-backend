import { afterEach, describe, expect, it, vi } from 'vitest';
import { createCourse, deleteCourse, listCourses, listSummary, updateCourse } from '@/features/courses/api/coursesApi';
import { courseToForm } from '@/features/courses/model/courseForm';
import { course, mockFetch } from '@/test/fixtures';

afterEach(() => vi.unstubAllGlobals());

describe('servidor', () => {
  it('lista, crea, edita y borra cursos', async () => {
    const c = course();
    const calls = mockFetch({ body: [c] }, { status: 201, body: c }, { body: c }, { status: 204 }, { body: [{ courseId: 'c1', unitId: 'u1', approved: 1, pending: 2 }] });
    expect(await listCourses()).toHaveLength(1);
    await createCourse(courseToForm(c));
    await updateCourse(c, courseToForm(c));
    await deleteCourse('c 1');
    expect((await listSummary())[0].pending).toBe(2);
    expect(calls.map((x) => `${x.method} ${x.url}`)).toEqual([
      'GET /api/v1/cursos',
      'POST /api/v1/cursos',
      'PUT /api/v1/cursos/c1',
      'DELETE /api/v1/cursos/c%201',
      'GET /api/v1/resumen',
    ]);
  });
});
