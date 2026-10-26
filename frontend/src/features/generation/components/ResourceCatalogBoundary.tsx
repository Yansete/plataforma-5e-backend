/** Evita mostrar opciones inventadas o enviar peticiones antes de recibir el catálogo. */
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Alert, Button, Spinner } from '@/shared/components/ui';
import { errorMessage } from '@/shared/api/httpClient';
import { RESOURCE_TYPES } from '@/features/generation/model/resourceCatalog';
import { loadResourceCatalog } from '@/features/generation/api/resourceCatalogApi';

export function ResourceCatalogBoundary({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(RESOURCE_TYPES.length > 0);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      await loadResourceCatalog();
      setReady(true);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => { if (!ready) void load(); }, [ready, load]);
  if (ready) return <>{children}</>;
  if (error) return (
    <Alert tone="warn" title="No se pudieron cargar los tipos de recurso" role="alert">
      <p>{error}</p>
      <Button onClick={() => void load()} loading={busy}>Reintentar</Button>
    </Alert>
  );
  return <Spinner label="Cargando los tipos de recurso…" />;
}
