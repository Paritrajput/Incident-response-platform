import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";

import Navbar from "../components/Navbar";
import IncidentCard from "../components/IncidentCard";
import StatsBar from "../components/StatsBar";

import { useApplications } from "../context/ApplicationContext";
import { applicationsApi } from "../services/api";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";

export default function Dashboard() {
  const navigate = useNavigate();

  const { selectedApplication } = useApplications();

  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);

  const [incidents, setIncidents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deploys, setDeploys] = useState([]);
  const [integrations, setIntegrations] = useState([]);
  const [activeView, setActiveView] = useState("incidents");

  /**
   * ----------------------------
   * Health Check
   * ----------------------------
   */

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/health`,
      );

      const data = await res.json();

      setHealth(data);
    } catch {
      setHealth({
        status: "error",
      });
    }
  }, []);

  /**
   * ----------------------------
   * Load Incident History
   * ----------------------------
   */

  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);

      if (!selectedApplication) {
        setIncidents([]);
        return;
      }

      const data = await applicationsApi.incidents(selectedApplication.id);

      setIncidents([...(data.incidents || [])].reverse());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedApplication]);

  const loadDeploys = useCallback(async () => {
    if (!selectedApplication) {
      setDeploys([]);
      return;
    }
    try {
      const data = await applicationsApi.deploys(selectedApplication.id);
      setDeploys(data.deploys || data || []);
    } catch {
      // Deploy history is optional for an application that has no GitHub integration yet.
      setDeploys([]);
    }
  }, [selectedApplication]);

  const loadIntegrations = useCallback(async () => {
    if (!selectedApplication) {
      setIntegrations([]);
      return;
    }
    try {
      const data = await applicationsApi.integrations(selectedApplication.id);
      setIntegrations(
        Array.isArray(data) ? data : data.integrations || [],
      );
    } catch {
      setIntegrations([]);
    }
  }, [selectedApplication]);

  /**
   * ----------------------------
   * WebSocket
   * ----------------------------
   */

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(WS_URL);

    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const incident = JSON.parse(event.data);

      if (incident.application_id !== selectedApplication?.id) return;

      setIncidents((prev) => {
        const exists = prev.some((item) => item.trace_id === incident.trace_id);

        if (exists) return prev;

        return [incident, ...prev].slice(0, 50);
      });
    };

    ws.onclose = () => {
      setConnected(false);

      reconnectTimeout.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [selectedApplication?.id]);

  /**
   * ----------------------------
   * Initial Load
   * ----------------------------
   */

  useEffect(() => {
    setIncidents([]);
    setDeploys([]);
    loadHistory();
    loadDeploys();
    loadIntegrations();

    checkHealth();

    const interval = setInterval(checkHealth, 30000);

    connect();

    return () => {
      clearInterval(interval);

      clearTimeout(reconnectTimeout.current);

      wsRef.current?.close();
    };
  }, [
    checkHealth,
    connect,
    loadHistory,
    loadDeploys,
    loadIntegrations,
    selectedApplication?.id,
  ]);

  const integrationTypes = [
    {
      type: "prometheus",
      label: "Prometheus",
      detail: "Metrics monitoring",
      icon: "📊",
    },
    {
      type: "github",
      label: "GitHub",
      detail: "Deploy correlation",
      icon: "🚀",
    },
    {
      type: "slack",
      label: "Slack",
      detail: "Incident notifications",
      icon: "💬",
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      {/* Navbar */}

      <Navbar showLinks={false} />

      {/* Main Content */}

      <div className="mx-auto max-w-7xl px-6 py-8">
        {/* Header */}

        <div className="mb-8 flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div>
            <h1 className="text-3xl font-bold text-[var(--text-primary)]">
              {selectedApplication?.name}
            </h1>

            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Application dashboard ·{" "}
              {selectedApplication?.description ||
                "Monitor integrations, incidents, and deployments."}
            </p>
          </div>

          {/* Status Cards */}

          <div className="flex flex-wrap gap-3">
            {/* Live */}

            <div className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg-subtle)] px-4 py-3">
              <div
                className={`h-3 w-3 rounded-full ${
                  connected ? "bg-green-500" : "bg-red-500"
                }`}
              />

              <div>
                <p className="text-xs text-[var(--text-secondary)]">
                  WebSocket
                </p>

                <p
                  className={`text-sm font-semibold ${
                    connected ? "text-green-500" : "text-red-500"
                  }`}
                >
                  {connected ? "Connected" : "Disconnected"}
                </p>
              </div>
            </div>

            {/* Backend */}

            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-subtle)] px-4 py-3">
              <p className="text-xs text-[var(--text-secondary)]">Backend</p>

              <p
                className={`text-sm font-semibold ${
                  health?.status === "ok" ? "text-green-500" : "text-yellow-500"
                }`}
              >
                {health?.status === "ok" ? "Operational" : "Checking..."}
              </p>
            </div>

            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-subtle)] px-4 py-3">
              <p className="text-xs text-[var(--text-secondary)]">
                Application status
              </p>
              <p className="text-sm font-semibold capitalize text-[var(--text-primary)]">
                {selectedApplication?.status || "active"}
              </p>
            </div>
          </div>
        </div>

        {/* Stats */}

        <StatsBar incidents={incidents} />

        <section className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-[var(--text-primary)]">
                Application integrations
              </h2>
              <p className="text-sm text-[var(--text-secondary)]">
                Connections configured for this application only.
              </p>
            </div>
            <button
              onClick={() => navigate("/onboarding")}
              className="btn-secondary"
            >
              Manage integrations
            </button>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {integrationTypes.map((item) => {
              const connectedIntegration = integrations.find(
                (integration) =>
                  integration.type === item.type && integration.enabled,
              );
              return (
                <div
                  key={item.type}
                  className="card flex items-center gap-3 p-4"
                >
                  <span className="text-xl">{item.icon}</span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[var(--text-primary)]">
                      {item.label}
                    </p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      {item.detail}
                    </p>
                  </div>
                  <span
                    className={`badge ${connectedIntegration ? "bg-green-500/10 text-green-500" : "bg-[var(--bg-subtle)] text-[var(--text-muted)]"}`}
                  >
                    {connectedIntegration ? "Connected" : "Not connected"}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Remaining content (Incident List / Empty State)
            goes in Part 2 */}
        {/* Content */}

        <section className="mt-8">
          <div className="mb-5 flex gap-2 border-b border-[var(--border)]">
            <button
              onClick={() => setActiveView("incidents")}
              className={`px-4 py-3 text-sm font-medium ${activeView === "incidents" ? "border-b-2 border-[var(--accent)] text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}`}
            >
              Incident history{" "}
              <span className="ml-1 text-xs">{incidents.length}</span>
            </button>
            <button
              onClick={() => setActiveView("deploys")}
              className={`px-4 py-3 text-sm font-medium ${activeView === "deploys" ? "border-b-2 border-[var(--accent)] text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}`}
            >
              Deploy history{" "}
              <span className="ml-1 text-xs">{deploys.length}</span>
            </button>
          </div>

          {activeView === "deploys" ? (
            deploys.length === 0 ? (
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-subtle)] p-12 text-center">
                <h2 className="text-lg font-semibold text-[var(--text-primary)]">
                  No deployments recorded
                </h2>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  Connect GitHub to correlate deployments with incidents for{" "}
                  {selectedApplication?.name}.
                </p>
              </div>
            ) : (
              <div className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--bg-subtle)]">
                {deploys.map((deploy) => (
                  <div
                    key={deploy.id || `${deploy.deploy_id}-${deploy.timestamp}`}
                    className="grid gap-2 border-b border-[var(--border)] p-4 text-sm last:border-0 md:grid-cols-[1fr_auto_auto]"
                  >
                    <span className="font-medium text-[var(--text-primary)]">
                      {deploy.service}
                    </span>
                    <span className="text-[var(--text-secondary)]">
                      {deploy.branch || "default branch"}
                    </span>
                    <span className="text-[var(--text-secondary)]">
                      {deploy.commit_message || deploy.deploy_id}
                    </span>
                  </div>
                ))}
              </div>
            )
          ) : loading ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--bg-subtle)] py-20">
              <div className="mb-4 h-10 w-10 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--accent)]" />

              <h2 className="text-lg font-semibold text-[var(--text-primary)]">
                Loading incidents...
              </h2>

              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                Fetching incident history from the server.
              </p>
            </div>
          ) : incidents.length === 0 ? (
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-subtle)] p-16 text-center">
              <div className="mb-6 text-6xl">🚨</div>

              <h2 className="text-2xl font-bold text-[var(--text-primary)]">
                No incidents detected
              </h2>

              <p className="mx-auto mt-4 max-w-xl text-[15px] leading-7 text-[var(--text-secondary)]">
                Your monitoring pipeline is connected but no incidents have been
                generated yet. Connect your services or start the simulator to
                begin receiving live AI incident analysis.
              </p>

              <div className="mt-8 flex justify-center gap-4">
                <button
                  onClick={() => navigate("/onboarding")}
                  className="btn-primary"
                >
                  Connect Integrations
                </button>

                <button onClick={loadHistory} className="btn-secondary">
                  Refresh
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {incidents.map((incident) => (
                <IncidentCard key={incident.trace_id} incident={incident} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
