import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Alert, Breadcrumb, Button, ButtonLink, Card, CardHeader, ConfirmDialog, EmptyState, PageHeader, TextField } from '@/shared/components/ui';
import { errorMessage } from '@/shared/api/httpClient';
import { createCourse, deleteCourse, updateCourse } from '@/features/courses/api/coursesApi';
import { courseFormProblem, courseToForm, emptyCourseForm, type CourseForm } from '@/features/courses/model/courseForm';
import { useData } from '@/app/DataProvider';
import type { Course } from '@/shared/types/domain';
import { CoursesLoading } from '@/features/courses/components/CoursesLoading';
import { usePageTitle } from '@/shared/hooks/usePageTitle';

export function CourseFormPage() {
  const { courseId } = useParams();
  const { courses } = useData();
  const editing = Boolean(courseId);
  const course = courseId ? courses?.find((c) => c.id === courseId) : undefined;

  if (editing && courses === null) return <CoursesLoading />;
  if (editing && !course)
    return (
      <EmptyState icon="book" title="No encontramos este curso" action={<ButtonLink to="/courses">Volver a Mis cursos</ButtonLink>}>
        Puede que se haya borrado.
      </EmptyState>
    );
  return <CourseFormView key={course?.id ?? 'nuevo'} course={course} />;
}

function CourseFormView({ course }: { course?: Course }) {
  const navigate = useNavigate();
  const { saveCourseLocally, removeCourseLocally, reloadSummary } = useData();
  const [form, setForm] = useState<CourseForm>(() => (course ? courseToForm(course) : emptyCourseForm()));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  usePageTitle(course ? `Editar ${course.code}` : 'Nuevo curso');

  useEffect(() => setError(''), [form]);

  const set = <K extends keyof CourseForm>(key: K, value: CourseForm[K]) => setForm((f) => ({ ...f, [key]: value }));
  const setUnit = (index: number, key: 'title' | 'outcomes', value: string) =>
    setForm((f) => ({ ...f, units: f.units.map((u, i) => (i === index ? { ...u, [key]: value } : u)) }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = courseFormProblem(form);
    if (problem) {
      setError(problem);
      return;
    }
    setSaving(true);
    try {
      const saved = course ? await updateCourse(course, form) : await createCourse(form);
      saveCourseLocally(saved);
      void reloadSummary();
      navigate(`/courses/${saved.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!course) return;
    setDeleting(true);
    try {
      await deleteCourse(course.id);
      removeCourseLocally(course.id);
      navigate('/courses', { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setConfirmDelete(false);
      setDeleting(false);
    }
  };

  const title = course ? 'Editar curso' : 'Nuevo curso';
  return (
    <form className="stack stack--loose" onSubmit={submit} noValidate>
      <Breadcrumb items={[{ label: 'Mis cursos', to: '/courses' }, ...(course ? [{ label: `${course.code} · ${course.name}`, to: `/courses/${course.id}` }] : []), { label: title }]} />
      <PageHeader title={title} description="La sumilla, el logro y los resultados de aprendizaje guían a la IA para que los recursos respondan a tu sílabo." />

      <Card>
        <CardHeader title="Datos del curso" />
        <div className="form-grid form-grid--3">
          <TextField label="Código" value={form.code} onChange={(v) => set('code', v)} maxLength={30} placeholder="RED-301" />
          <TextField label="Nombre del curso" value={form.name} onChange={(v) => set('name', v)} maxLength={150} placeholder="Redes de Computadoras" />
          <TextField label="Periodo" value={form.term} onChange={(v) => set('term', v)} maxLength={30} placeholder="2026-II" />
        </div>
        <TextField label="Sumilla" multiline rows={4} value={form.summary} onChange={(v) => set('summary', v)} maxLength={3000} hint="Opcional. Cópiala de tu sílabo." />
        <TextField label="Logro del curso" multiline rows={3} value={form.learningGoal} onChange={(v) => set('learningGoal', v)} maxLength={1000} hint="Opcional." />
      </Card>

      <Card>
        <CardHeader title="Unidades y resultados de aprendizaje" description="Escribe un resultado por línea. Los códigos RA1.1, RA1.2… se ponen solos." />
        <div className="stack">
          {form.units.map((unit, index) => (
            <fieldset key={unit.id ?? `nueva-${index}`} className="unit-fieldset">
              <legend className="unit-fieldset__legend">
                <span>Unidad {index + 1}</span>
                {!unit.id && form.units.length > 1 && (
                  <Button compact icon="trash" onClick={() => setForm((f) => ({ ...f, units: f.units.filter((_, i) => i !== index) }))}>
                    Quitar unidad
                  </Button>
                )}
              </legend>
              <TextField label="Título de la unidad" value={unit.title} onChange={(v) => setUnit(index, 'title', v)} maxLength={150} />
              <TextField
                label="Resultados de aprendizaje"
                multiline
                rows={3}
                value={unit.outcomes}
                onChange={(v) => setUnit(index, 'outcomes', v)}
                hint="Uno por línea. Puedes empezar con su código: «RA1.2: Compara…»."
              />
            </fieldset>
          ))}
          <div>
            <Button icon="plus" onClick={() => setForm((f) => ({ ...f, units: [...f.units, { title: '', outcomes: '' }] }))}>
              Añadir unidad
            </Button>
          </div>
          {course && <p className="caption">Las unidades guardadas no se pueden quitar porque pueden tener material y recursos. Si ya no usas el curso, bórralo completo.</p>}
        </div>
      </Card>

      {error && (
        <Alert tone="warn" role="alert">
          {error}
        </Alert>
      )}
      <div className="btn-row">
        <Button type="submit" variant="primary" loading={saving}>
          Guardar curso
        </Button>
        <ButtonLink to={course ? `/courses/${course.id}` : '/courses'}>Cancelar</ButtonLink>
      </div>

      {course && (
        <Card className="card--danger">
          <CardHeader
            title="Borrar el curso"
            description="Se borran sus unidades, el material subido, los recursos generados y el historial de descargas. No se puede deshacer."
            actions={
              <Button variant="danger" icon="trash" onClick={() => setConfirmDelete(true)}>
                Borrar curso
              </Button>
            }
          />
        </Card>
      )}

      <ConfirmDialog
        open={confirmDelete}
        title={`¿Borrar ${course?.code ?? 'el curso'}?`}
        confirmLabel="Borrar curso"
        confirmVariant="danger"
        confirmLoading={deleting}
        onConfirm={() => void remove()}
        onCancel={() => setConfirmDelete(false)}
      >
        <p>Se borrarán sus {course?.units.length ?? 0} unidades con todo su material, recursos e historial de descargas. Esta acción no se puede deshacer.</p>
      </ConfirmDialog>
    </form>
  );
}
