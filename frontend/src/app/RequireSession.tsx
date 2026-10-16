import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useSession } from '@/app/DataProvider';

export function RequireSession() {
  const session = useSession();
  const location = useLocation();
  return session ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname + location.search + location.hash }} />;
}
