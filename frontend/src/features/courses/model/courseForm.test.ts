import { describe, expect, it } from 'vitest';
import { courseFormProblem, courseRequest, courseToForm, emptyCourseForm, findUnit, outcomeLines, parseOutcomeLines } from '@/features/courses/model/courseForm';
import { course, unit } from '@/test/fixtures';

describe('resultados de aprendizaje', () => {
  it('lee un resultado por línea y conserva el código escrito', () => {
    expect(parseOutcomeLines('RA1.2: Compara modelos\n\n  Explica capas  \nra 3) Calcula subredes')).toEqual([
      { code: 'RA1.2', text: 'Compara modelos' },
      { text: 'Explica capas' },
      { code: 'RA 3', text: 'Calcula subredes' },
    ]);
  });

  it('al editar conserva el id y el código de cada línea', () => {
    const previous = unit().outcomes;
    expect(parseOutcomeLines('Nuevo texto\nRA9.9: Otro', previous)).toEqual([
      { id: 'ra1', code: 'RA1.1', text: 'Nuevo texto' },
      { id: 'ra2', code: 'RA9.9', text: 'Otro' },
    ]);
    expect(outcomeLines(previous)).toBe(`RA1.1: ${previous[0].text}\nRA1.2: ${previous[1].text}`);
  });
});

describe('formulario del curso', () => {
  it('empieza con una unidad vacía y avisa lo que falta', () => {
    const form = emptyCourseForm();
    expect(form.units).toHaveLength(1);
    expect(courseFormProblem(form)).toMatch(/código/);
    expect(courseFormProblem({ ...form, code: 'A', name: 'B', term: 'C' })).toMatch(/título de cada unidad/);
    expect(courseFormProblem({ ...form, code: 'A', name: 'B', term: 'C', units: [] })).toMatch(/al menos una unidad/);
    expect(courseFormProblem({ ...form, code: 'A', name: 'B', term: 'C', units: [{ title: 'U1', outcomes: '' }] })).toBeNull();
  });

  it('convierte un curso en formulario y de vuelta en la petición', () => {
    const c = course({ summary: undefined, learningGoal: undefined });
    const form = courseToForm(c);
    expect(form).toMatchObject({ code: 'RED-301', summary: '', learningGoal: '', units: [{ id: 'u1', title: c.units[0].title }] });
    const request = courseRequest({ ...form, name: '  Redes  ', units: [...form.units, { title: ' Nueva ', outcomes: 'Calcula subredes' }] }, c);
    expect(request.name).toBe('Redes');
    expect(request.units[0]).toMatchObject({ id: 'u1', outcomes: [{ id: 'ra1', code: 'RA1.1' }, { id: 'ra2', code: 'RA1.2' }] });
    expect(request.units[1]).toEqual({ title: 'Nueva', outcomes: [{ text: 'Calcula subredes' }] });
  });

  it('busca una unidad entre los cursos', () => {
    expect(findUnit([course()], 'u1')?.unit.number).toBe(1);
    expect(findUnit([course()], 'otra')).toBeNull();
  });
});
