import { Link } from 'react-router-dom';
import { ButtonLink, EmptyState, PageHeader } from '@/shared/components/ui';
import { Icon } from '@/shared/components/Icon';
import { useData } from '@/app/DataProvider';
import { plural } from '@/shared/lib/format';
import { CoursesLoading } from '@/features/courses/components/CoursesLoading';
import { usePageTitle } from '@/shared/hooks/usePageTitle';

export function CourseListPage() {
  const { courses, documents, summary } = useData();
  usePageTitle('Mis cursos');

  return (
    <div className="stack stack--loose">
      <PageHeader
        title="Mis cursos"
        description="Entra a un curso para trabajar sus unidades, o crea uno nuevo."
        actions={
          <ButtonLink to="/courses/new" variant="primary" icon="plus">
            Nuevo curso
          </ButtonLink>
        }
      />
      {courses === null ? (
        <CoursesLoading />
      ) : courses.length === 0 ? (
        <EmptyState
          icon="book"
          title="Todavía no tienes cursos"
          action={
            <ButtonLink to="/courses/new" variant="primary" icon="plus">
              Crear mi primer curso
            </ButtonLink>
          }
        >
          Registra tu curso con sus unidades y resultados de aprendizaje. Después podrás subir material a cada unidad y generar recursos.
        </EmptyState>
      ) : (
        <div className="course-grid">
          {courses.map((course) => {
            const unitIds = new Set(course.units.map((u) => u.id));
            const docs = documents.filter((d) => unitIds.has(d.unitId)).length;
            const approved = summary.filter((s) => s.courseId === course.id).reduce((n, s) => n + s.approved, 0);
            return (
              <article key={course.id} className="card course-card">
                <span className="overline">
                  {course.code} · {course.term}
                </span>
                <h2 className="h2">{course.name}</h2>
                {course.summary && <p className="course-card__text">{course.summary.length > 170 ? `${course.summary.slice(0, 170).trimEnd()}…` : course.summary}</p>}
                <p className="course-card__stats">
                  <span>{plural(course.units.length, 'unidad', 'unidades')}</span>
                  <span>{plural(docs, 'documento', 'documentos')}</span>
                  <span>{plural(approved, 'recurso aprobado', 'recursos aprobados')}</span>
                </p>
                <div className="btn-row">
                  <ButtonLink to={`/courses/${course.id}`} variant="primary">
                    Entrar al curso
                  </ButtonLink>
                  <ButtonLink to={`/courses/${course.id}/edit`}>Editar</ButtonLink>
                </div>
              </article>
            );
          })}
          <Link to="/courses/new" className="card course-card course-card--new">
            <span className="course-card__plus" aria-hidden="true">
              <Icon name="plus" />
            </span>
            <span className="title">Nuevo curso</span>
            <span className="caption">Registra el curso con sus unidades y resultados de aprendizaje.</span>
          </Link>
        </div>
      )}
    </div>
  );
}
