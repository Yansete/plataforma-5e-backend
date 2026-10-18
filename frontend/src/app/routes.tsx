import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { RequireSession } from '@/app/RequireSession';
import { NotFoundPage } from '@/app/NotFoundPage';
import { AppLayout } from '@/shared/components/AppLayout';
import { Spinner } from '@/shared/components/ui';
import { LoginPage } from '@/features/auth/pages/LoginPage';

// Cada pantalla se descarga al abrirla: /login no carga el código de cursos, unidades, revisión ni exportación.
const RegisterPage = lazy(() => import('@/features/auth/pages/RegisterPage').then((m) => ({ default: m.RegisterPage })));
const CourseListPage = lazy(() => import('@/features/courses/pages/CourseListPage').then((m) => ({ default: m.CourseListPage })));
const CourseDetailPage = lazy(() => import('@/features/courses/pages/CourseDetailPage').then((m) => ({ default: m.CourseDetailPage })));
const CourseFormPage = lazy(() => import('@/features/courses/pages/CourseFormPage').then((m) => ({ default: m.CourseFormPage })));
const UnitPage = lazy(() => import('@/features/units/pages/UnitPage').then((m) => ({ default: m.UnitPage })));

export function AppRoutes() {
  return (
    <Routes>
      <Route path="login" element={<LoginPage />} />
      <Route
        path="register"
        element={
          <Suspense fallback={<Spinner label="Cargando…" />}>
            <RegisterPage />
          </Suspense>
        }
      />
      <Route element={<RequireSession />}>
        {/* AppLayout envuelve el contenido en Suspense: el menú lateral queda visible mientras carga la pantalla. */}
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/courses" replace />} />
          <Route path="courses" element={<CourseListPage />} />
          <Route path="courses/new" element={<CourseFormPage />} />
          <Route path="courses/:courseId" element={<CourseDetailPage />} />
          <Route path="courses/:courseId/edit" element={<CourseFormPage />} />
          <Route path="courses/:courseId/units/:unitId" element={<UnitPage />} />
          <Route path="courses/:courseId/units/:unitId/:tab" element={<UnitPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
