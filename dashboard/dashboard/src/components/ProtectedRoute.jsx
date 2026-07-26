import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
    const { loading, isAuthenticated } = useAuth();

    // Wait until authentication status is determined
    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-lg font-medium">
                    Loading...
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return <Outlet />;
}