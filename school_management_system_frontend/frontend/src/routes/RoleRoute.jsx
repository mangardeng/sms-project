import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

/** Restricts a route subtree to specific roles; anyone else is bounced to their own dashboard. */
export default function RoleRoute({ roles }) {
  const { user } = useAuth();

  if (!user) return null; // ProtectedRoute above this already handles the unauthenticated case.

  if (!roles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
