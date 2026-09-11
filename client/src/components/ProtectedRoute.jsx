import { Navigate, Outlet, useLocation } from 'react-router-dom';

export default function ProtectedRoute() {
  const location = useLocation();
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');

  // Dev-only bypass: keeps preview functionality accessible when backend is offline
  const devPreviewAllowed = import.meta.env.DEV;

  if (!token && !devPreviewAllowed) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <Outlet />;
}