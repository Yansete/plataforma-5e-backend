import { useEffect } from 'react';

/** Título de la pestaña del navegador. */
export function usePageTitle(title: string): void {
  useEffect(() => {
    document.title = `${title} · Plataforma Docente`;
  }, [title]);
}
