import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function ProtectedRoute({ children }) {
  const { session, loading } = useAuth();
  const location = useLocation();
  if (loading) return null;
  if (!session) return <Navigate to="/login" state={{ from: location }} replace />;
  return children;
}
