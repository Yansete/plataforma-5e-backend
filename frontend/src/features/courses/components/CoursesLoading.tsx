/** Estados comunes de las pantallas con datos del servidor: cargando y error al cargar. */
import { Alert, Button, Spinner } from '@/shared/components/ui';
import { useData } from '@/app/DataProvider';
import { useSlowNotice } from '@/shared/hooks/useSlowNotice';

/** Muestra «Cargando…» o el error de carga. Devuelve null cuando los cursos ya están listos. */
export function CoursesLoading() {
  const { courses, error, reload } = useData();
  const slow = useSlowNotice(courses === null && !error);
  if (error)
    return (
      <div className="stack">
        <Alert tone="warn" title="No se pudieron cargar tus datos" role="alert">
          {error}
        </Alert>
        <div className="btn-row">
          <Button variant="primary" icon="refresh" onClick={() => void reload()}>
            Reintentar
          </Button>
        </div>
      </div>
    );
  return (
    <div className="stack">
      <Spinner label="Cargando tus cursos…" />
      {slow && <p className="caption">La primera conexión del día puede tardar hasta un minuto mientras el servidor se activa.</p>}
    </div>
  );
}
