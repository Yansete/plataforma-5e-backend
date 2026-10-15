import type { Course, LearningOutcome, Unit } from '@/shared/types/domain';

export interface UnitForm {
  /** Solo en unidades ya guardadas. */
  id?: string;
  title: string;
  /** Un resultado por línea; puede empezar con su código («RA1.1: …»). */
  outcomes: string;
}

export interface CourseForm {
  code: string;
  name: string;
  term: string;
  sumilla: string;
  logro: string;
  units: UnitForm[];
}

export interface OutcomeInput {
  id?: string;
  code?: string;
  text: string;
}

const CODE_PREFIX = /^([A-Za-z]{1,4}[ -]?\d+(?:\.\d+)*)\s*[:.)-]\s+(.+)$/;

/** Una línea por resultado. «RA1.2: Compara modelos» conserva el código; sin código se numera solo. */
export function parseOutcomeLines(text: string, previous: LearningOutcome[] = []): OutcomeInput[] {
  return text.split('\n').map((line) => line.trim()).filter(Boolean).map((line, index) => {
    const match = line.match(CODE_PREFIX);
    const old = previous[index];
    return {
      ...(old ? { id: old.id } : {}),
      ...(match ? { code: match[1].toUpperCase() } : old ? { code: old.code } : {}),
      text: match ? match[2].trim() : line,
    };
  });
}

/** Texto editable de los resultados de una unidad: «código: texto», uno por línea. */
export function outcomeLines(outcomes: LearningOutcome[]): string {
  return outcomes.map((o) => `${o.code}: ${o.text}`).join('\n');
}

export function emptyCourseForm(): CourseForm {
  return { code: '', name: '', term: '', sumilla: '', logro: '', units: [{ title: '', outcomes: '' }] };
}

export function courseToForm(course: Course): CourseForm {
  return {
    code: course.code,
    name: course.name,
    term: course.term,
    sumilla: course.sumilla ?? '',
    logro: course.logro ?? '',
    units: course.units.map((u) => ({ id: u.id, title: u.title, outcomes: outcomeLines(u.outcomes) })),
  };
}

/** Revisa el formulario antes de enviarlo. Devuelve el primer problema o null. */
export function courseFormProblem(form: CourseForm): string | null {
  if (!form.code.trim() || !form.name.trim() || !form.term.trim()) return 'Completa el código, el nombre y el periodo del curso.';
  if (!form.units.length) return 'Agrega al menos una unidad.';
  if (form.units.some((u) => !u.title.trim())) return 'Escribe el título de cada unidad.';
  return null;
}

export function courseRequest(form: CourseForm, previous?: Course) {
  return {
    code: form.code.trim(),
    name: form.name.trim(),
    term: form.term.trim(),
    sumilla: form.sumilla.trim(),
    logro: form.logro.trim(),
    units: form.units.map((u) => {
      const before = previous?.units.find((p) => p.id === u.id);
      return { ...(u.id ? { id: u.id } : {}), title: u.title.trim(), outcomes: parseOutcomeLines(u.outcomes, before?.outcomes) };
    }),
  };
}

export function findUnit(courses: Course[], unitId: string): { course: Course; unit: Unit } | null {
  for (const course of courses) {
    const unit = course.units.find((u) => u.id === unitId);
    if (unit) return { course, unit };
  }
  return null;
}
