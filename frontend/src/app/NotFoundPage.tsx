import { ButtonLink, EmptyState } from '@/shared/components/ui';
import { usePageTitle } from '@/shared/hooks/usePageTitle';

export function NotFoundPage() {
  usePageTitle('Página no encontrada');
  return (
    <EmptyState icon="info" title="No encontramos esta página" action={<ButtonLink to="/courses" variant="primary">Ir a Mis cursos</ButtonLink>}>
      Revisa la dirección o vuelve a tus cursos.
    </EmptyState>
  );
}
