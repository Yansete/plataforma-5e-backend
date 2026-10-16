import { useParams } from 'react-router-dom';
import { Breadcrumb, ButtonLink, Card, EmptyState, PageHeader } from '../components/ui';
import { Icon } from '../components/Icon';
import { materialSummary, unitDocuments } from '../services/material';
import { useData } from '../state/datos';
import { plural } from '../utils/format';
import { LoadingCourses } from './estado';
import { usePageTitle } from './usePageTitle';

export function CursoPage() {
  const { courseId } = useParams();
  const { courses, documents, summary } = useData();
  const course = courses?.find((c) => c.id === courseId);
  usePageTitle(course ? `${course.code} · ${course.name}` : 'Curso');

  if (courses === null) return <LoadingCourses />;
  if (!course)
    return (
      <EmptyState icon="book" title="No encontramos este curso" action={<ButtonLink to="/">Volver a Mis cursos</ButtonLink>}>
        Puede que se haya borrado.
      </EmptyState>
    );

  return (
    <div className="stack stack--loose">
      <Breadcrumb items={[{ label: 'Mis cursos', to: '/' }, { label: `${course.code} · ${course.name}` }]} />
      <PageHeader
        overline={`${course.code} · ${course.term}`}
        title={course.name}
        actions={
          <ButtonLink to={`/cursos/${course.id}/editar`} icon="edit">
            Editar curso
          </ButtonLink>
        }
      />
      {(course.sumilla || course.logro) && (
        <Card className="course-info">
          {course.sumilla && (
            <div>
              <h2 className="overline">Sumilla</h2>
              <p>{course.sumilla}</p>
            </div>
          )}
          {course.logro && (
            <div>
              <h2 className="overline">Logro del curso</h2>
              <p>{course.logro}</p>
            </div>
          )}
        </Card>
      )}

      <section className="stack" aria-labelledby="unidades">
        <h2 className="h2" id="unidades">
          Unidades
        </h2>
        {course.units.map((unit) => {
          const material = materialSummary(unitDocuments(documents, unit.id));
          const resources = summary.find((s) => s.unitId === unit.id);
          const url = `/cursos/${course.id}/unidades/${unit.id}`;
          return (
            <article key={unit.id} className="card unit-card">
              <div className="unit-card__head">
                <div>
                  <span className="overline">Unidad {unit.number}</span>
                  <h3 className="title">{unit.title}</h3>
                </div>
                <ButtonLink to={url} variant="primary" icon="arrowRight">
                  Abrir unidad
                </ButtonLink>
              </div>
              {unit.outcomes.length > 0 && (
                <ul className="outcome-list">
                  {unit.outcomes.map((o) => (
                    <li key={o.id}>
                      <strong>{o.code}</strong> {o.text}
                    </li>
                  ))}
                </ul>
              )}
              {material.processed > 0 ? (
                <p className="unit-card__stats">
                  <span>
                    <strong>Material:</strong> {plural(material.processed, 'documento', 'documentos')} · {plural(material.fragments, 'fragmento', 'fragmentos')}
                  </span>
                  <span>
                    <strong>Recursos:</strong> {resources && resources.approved + resources.pending > 0 ? `${plural(resources.approved, 'aprobado', 'aprobados')} · ${resources.pending} por revisar` : 'todavía no hay'}
                  </span>
                </p>
              ) : (
                <p className="unit-card__empty">
                  <Icon name="info" size={16} />
                  <span>
                    <strong>Sin material todavía.</strong> Sube un documento o busca el tema para empezar a generar.
                  </span>
                </p>
              )}
            </article>
          );
        })}
      </section>
    </div>
  );
}
