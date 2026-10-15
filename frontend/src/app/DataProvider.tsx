/**
 * Datos del docente que comparten varias pantallas: cursos, documentos y el resumen de recursos.
 * Se cargan del servidor al entrar y cada pantalla pide recargar lo que cambió.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from 'react';
import { errorMessage } from '@/shared/api/httpClient';
import { getSession, onSessionChange } from '@/shared/api/sessionStore';
import { listCourses, listSummary } from '@/features/courses/api/coursesApi';

import { listDocuments } from '@/features/materials/api/materialsApi';
import type { Course, MaterialDocument, Session, UnitSummary } from '@/shared/types/domain';

export function useSession(): Session | null {
  return useSyncExternalStore(onSessionChange, getSession, getSession);
}

interface DataValue {
  /** null mientras se cargan por primera vez. */
  courses: Course[] | null;
  documents: MaterialDocument[];
  summary: UnitSummary[];
  error: string;
  reload: () => Promise<void>;
  reloadDocuments: () => Promise<void>;
  reloadSummary: () => Promise<void>;
  saveCourseLocally: (course: Course) => void;
  removeCourseLocally: (courseId: string) => void;
}

const DataContext = createContext<DataValue | null>(null);

export function DataProvider({ children }: { children: ReactNode }) {
  const session = useSession();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [documents, setDocuments] = useState<MaterialDocument[]>([]);
  const [summary, setSummary] = useState<UnitSummary[]>([]);
  const [error, setError] = useState('');

  const reload = useCallback(async () => {
    setError('');
    try {
      const [c, d, s] = await Promise.all([listCourses(), listDocuments(), listSummary()]);
      setCourses(c);
      setDocuments(d);
      setSummary(s);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  const reloadDocuments = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
    } catch {
      /* la pantalla que pidió recargar muestra su propio error */
    }
  }, []);

  const reloadSummary = useCallback(async () => {
    try {
      setSummary(await listSummary());
    } catch {
      /* el resumen es informativo: si falla, se conserva el anterior */
    }
  }, []);

  useEffect(() => {
    if (!session) {
      setCourses(null);
      setDocuments([]);
      setSummary([]);
      return;
    }
    void reload();
  }, [session?.token, reload]);

  const value = useMemo<DataValue>(
    () => ({
      courses,
      documents,
      summary,
      error,
      reload,
      reloadDocuments,
      reloadSummary,
      saveCourseLocally: (course) =>
        setCourses((previous) => {
          const list = previous ?? [];
          return list.some((c) => c.id === course.id) ? list.map((c) => (c.id === course.id ? course : c)) : [...list, course];
        }),
      removeCourseLocally: (courseId) => {
        setCourses((previous) => (previous ?? []).filter((c) => c.id !== courseId));
        void reloadDocuments();
        void reloadSummary();
      },
    }),
    [courses, documents, summary, error, reload, reloadDocuments, reloadSummary],
  );

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useData(): DataValue {
  const value = useContext(DataContext);
  if (!value) throw new Error('useData debe usarse dentro de DataProvider');
  return value;
}
