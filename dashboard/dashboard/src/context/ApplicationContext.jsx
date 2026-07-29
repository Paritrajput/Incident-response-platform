import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { applicationsApi } from "../services/api";
import { useAuth } from "./AuthContext";

const ApplicationContext = createContext(null);
const STORAGE_KEY = "selected_application_id";

export function ApplicationProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [applications, setApplications] = useState([]);
  const [selectedApplication, setSelectedApplicationState] = useState(null);
  const [loadingApplications, setLoadingApplications] = useState(true);

  const setSelectedApplication = useCallback((application) => {
    setSelectedApplicationState(application || null);
    if (application?.id != null) localStorage.setItem(STORAGE_KEY, String(application.id));
    else localStorage.removeItem(STORAGE_KEY);
  }, []);

  const refreshApplications = useCallback(async () => {
    if (!isAuthenticated) {
      setApplications([]);
      setSelectedApplication(null);
      setLoadingApplications(false);
      return [];
    }

    setLoadingApplications(true);
    try {
      const data = await applicationsApi.list();
      const nextApplications = Array.isArray(data) ? data : data.applications || [];
      const savedId = localStorage.getItem(STORAGE_KEY);
      const currentId = selectedApplication?.id;
      const nextSelected = nextApplications.find((app) => String(app.id) === String(currentId))
        || nextApplications.find((app) => String(app.id) === savedId)
        || (nextApplications.length === 1 ? nextApplications[0] : null);

      setApplications(nextApplications);
      setSelectedApplication(nextSelected);
      return nextApplications;
    } finally {
      setLoadingApplications(false);
    }
  }, [isAuthenticated, selectedApplication?.id, setSelectedApplication]);

  useEffect(() => {
    refreshApplications().catch(() => {
      setApplications([]);
      setSelectedApplication(null);
      setLoadingApplications(false);
    });
  }, [refreshApplications]);

  return (
    <ApplicationContext.Provider value={{
      applications,
      selectedApplication,
      setSelectedApplication,
      refreshApplications,
      loadingApplications,
    }}>
      {children}
    </ApplicationContext.Provider>
  );
}

export function useApplications() {
  const context = useContext(ApplicationContext);
  if (!context) throw new Error("useApplications must be used inside ApplicationProvider.");
  return context;
}
