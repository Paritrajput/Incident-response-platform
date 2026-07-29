import { Navigate, Outlet } from "react-router-dom";
import { useApplications } from "../context/ApplicationContext";

export default function ApplicationGate() {
  const { loadingApplications, selectedApplication } = useApplications();

  if (loadingApplications) {
    return <div className="flex min-h-screen items-center justify-center text-[var(--text-secondary)]">Loading applications...</div>;
  }

  return selectedApplication ? <Outlet /> : <Navigate to="/applications" replace />;
}
