import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";

import Navbar from "../components/Navbar";
import IncidentCard from "../components/IncidentCard";
import StatsBar from "../components/StatsBar";

import api from "../services/api";
import { useAuth } from "../context/AuthContext";

const WS_URL =
  import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";

export default function Dashboard() {
  const navigate = useNavigate();

  const { user, logout } = useAuth();

  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);

  const [incidents, setIncidents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  /**
   * ----------------------------
   * Health Check
   * ----------------------------
   */

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/health`
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

      const data = await api.get("/incidents");

      setIncidents(
        [...(data.incidents || [])].reverse()
      );
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * ----------------------------
   * WebSocket
   * ----------------------------
   */

  const connect = useCallback(() => {
    if (
      wsRef.current &&
      wsRef.current.readyState === WebSocket.OPEN
    ) {
      return;
    }

    const ws = new WebSocket(WS_URL);

    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const incident = JSON.parse(event.data);

      setIncidents((prev) => {
        const exists = prev.some(
          (item) => item.trace_id === incident.trace_id
        );

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
  }, []);

  /**
   * ----------------------------
   * Initial Load
   * ----------------------------
   */

  useEffect(() => {
    loadHistory();

    checkHealth();

    const interval = setInterval(
      checkHealth,
      30000
    );

    connect();

    return () => {
      clearInterval(interval);

      clearTimeout(reconnectTimeout.current);

      wsRef.current?.close();
    };
  }, [checkHealth, connect, loadHistory]);

  /**
   * ----------------------------
   * Logout
   * ----------------------------
   */

  const handleLogout = async () => {
    await logout();

    navigate("/", {
      replace: true,
    });
  };

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
              Incident Feed
            </h1>

            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Live AI agent reasoning and incident timeline.
            </p>

          </div>

          {/* Status Cards */}

          <div className="flex flex-wrap gap-3">

            {/* Live */}

            <div className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg-subtle)] px-4 py-3">

              <div
                className={`h-3 w-3 rounded-full ${
                  connected
                    ? "bg-green-500"
                    : "bg-red-500"
                }`}
              />

              <div>

                <p className="text-xs text-[var(--text-secondary)]">
                  WebSocket
                </p>

                <p
                  className={`text-sm font-semibold ${
                    connected
                      ? "text-green-500"
                      : "text-red-500"
                  }`}
                >
                  {connected
                    ? "Connected"
                    : "Disconnected"}
                </p>

              </div>

            </div>

            {/* Backend */}

            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-subtle)] px-4 py-3">

              <p className="text-xs text-[var(--text-secondary)]">
                Backend
              </p>

              <p
                className={`text-sm font-semibold ${
                  health?.status === "ok"
                    ? "text-green-500"
                    : "text-yellow-500"
                }`}
              >
                {health?.status === "ok"
                  ? "Operational"
                  : "Checking..."}
              </p>

            </div>

            {/* User */}

            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-subtle)] px-4 py-3">

              <p className="text-xs text-[var(--text-secondary)]">
                Logged in as
              </p>

              <p className="max-w-56 truncate text-sm font-semibold text-[var(--text-primary)]">
                {user?.email}
              </p>

            </div>

          </div>

        </div>

        {/* Stats */}

        <StatsBar incidents={incidents} />

        {/* Remaining content (Incident List / Empty State)
            goes in Part 2 */}
        {/* Content */}

        <div className="mt-8">

          {loading ? (

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

              <div className="mb-6 text-6xl">
                🚨
              </div>

              <h2 className="text-2xl font-bold text-[var(--text-primary)]">
                No incidents detected
              </h2>

              <p className="mx-auto mt-4 max-w-xl text-[15px] leading-7 text-[var(--text-secondary)]">
                Your monitoring pipeline is connected but no incidents
                have been generated yet. Connect your services or start
                the simulator to begin receiving live AI incident analysis.
              </p>

              <div className="mt-8 flex justify-center gap-4">

                <button
                  onClick={() => navigate("/onboarding")}
                  className="btn-primary"
                >
                  Connect Integrations
                </button>

                <button
                  onClick={loadHistory}
                  className="btn-secondary"
                >
                  Refresh
                </button>

              </div>

            </div>

          ) : (

            <div className="space-y-5">

              {incidents.map((incident) => (

                <IncidentCard
                  key={incident.trace_id}
                  incident={incident}
                />

              ))}

            </div>

          )}

        </div>

      </div>

    </div>
  );
}