import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Alert, Button } from '@/shared/components/ui';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Evita la pantalla en blanco: si una pantalla falla al dibujarse, muestra un aviso y permite
 * volver a «Mis cursos» o recargar. El resto de la aplicación sigue funcionando (menú, sesión).
 * Se reinicia al cambiar de pantalla (`key` en AppLayout).
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Error al mostrar la pantalla', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="stack">
        <Alert tone="warn" title="No se pudo mostrar esta pantalla" role="alert">
          Ocurrió un error inesperado. Tus datos están guardados en el servidor y no se perdieron. Vuelve a «Mis cursos»
          o recarga la página.
        </Alert>
        <div className="btn-row">
          <Button variant="primary" icon="book" onClick={() => window.location.assign('/courses')}>
            Ir a Mis cursos
          </Button>
          <Button onClick={() => window.location.reload()}>Recargar la página</Button>
        </div>
      </div>
    );
  }
}
