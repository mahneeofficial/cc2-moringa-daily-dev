import { Navigate, Outlet } from "react-router-dom";
import { useSelector } from "react-redux";
import { selectCurrentUser } from "../features/auth/authSlice";

// ProtectedRoute only checks "is someone logged in" — this additionally
// checks "does that person's role allow this page", so typing /admin
// directly into the URL bar doesn't bypass role restrictions.
//
// Role comparison is case-insensitive: the backend stores "Admin" while
// routes allow "admin" — strict equality was locking real admins out.
export default function RoleRoute({ allow = [] }) {
  const user = useSelector(selectCurrentUser);

  const userRole = String(user?.role || "").toLowerCase();
  const allowed = allow.map((r) => String(r).toLowerCase());

  if (!user || !allowed.includes(userRole)) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
