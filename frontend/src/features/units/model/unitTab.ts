import type { Course, Resource, Unit } from '@/shared/types/domain';

export interface UnitTabProps {
  course: Course;
  unit: Unit;
  /** Ruta de la unidad, sin la pestaña. */
  base: string;
  /** null mientras se cargan. */
  resources: Resource[] | null;
  resourcesError: string;
  reloadResources: () => Promise<void>;
  upsertResources: (changed: Resource[]) => void;
  removeResource: (id: string) => void;
}
