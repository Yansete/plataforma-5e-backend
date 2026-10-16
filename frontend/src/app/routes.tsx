import { Navigate, Route, Routes } from 'react-router-dom';
import { RequireSession } from '@/app/RequireSession';
import { NotFoundPage } from '@/app/NotFoundPage';
import { AppLayout } from '@/shared/components/AppLayout';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { RegisterPage } from '@/features/auth/pages/RegisterPage';
import { CourseListPage } from '@/features/courses/pages/CourseListPage';
import { CourseDetailPage } from '@/features/courses/pages/CourseDetailPage';
import { CourseFormPage } from '@/features/courses/pages/CourseFormPage';
import { UnitPage } from '@/features/units/pages/UnitPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="login" element={<LoginPage />} />
      <Route path="register" element={<RegisterPage />} />
      <Route element={<RequireSession />}>
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
