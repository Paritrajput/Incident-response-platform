import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import IncidentCard from "../components/IncidentCard.jsx";
import StatsBar from "../components/StatsBar.jsx";
import { useTheme } from "../context/ThemeContext.jsx";

const WS_URL = `ws://${window.location.host}/ws`;
const API = "http://localhost:8000";

export default function Dashboard() {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const [incidents, setIncidents] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const email = localStorage.getItem("email") || "";

  useEffect(() => {
    connect();
    loadHistory();
    return () => wsRef.current?.close();
  }, []);

  function connect() {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => { setConnected(false); setTimeout(connect, 3000); };
    ws.onmessage = (e) => {
      const d = JSON.parse(e.data);
      setIncidents((prev) => [d, ...prev].slice(0, 50));
    };
  }

  async function loadHistory() {
    const key = localStorage.getItem("api_key");
    if (!key) return;
    try {
      const res = await fetch(`${API}/incidents/`, { headers: { "Authorization": `Bearer ${key}` } });
      if (res.ok) {
        const data = await res.json();
        setIncidents((prev) => prev.length === 0 ? [...data.incidents].reverse() : prev);
      }
    } catch (_) {}
  }

  function logout() {
    localStorage.clear();
    navigate("/");
  }

  return (
    <div style={{ background: "var(--bg-base)", minHeight: "100vh" }}>

      {/* Nav */}
      <nav style={{
        position: "sticky", top: 0, zIndex: 100,
        background: "var(--bg-base)", borderBottom: "1px solid var(--border)",
      }}>
        <div style={{
          maxWidth: 1100, margin: "0 auto", padding: "0 24px",
          height: 60, display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 28, height: 28, background: "var(--accent)",
              borderRadius: 8, display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: 14,
            }}>⚡</div>
            <span style={{ fontWeight: 700, fontSize: 16, color: "var(--text-primary)" }}>IncidentAI</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {/* Live indicator */}
            <div style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "5px 12px", borderRadius: 20,
              background: "var(--bg-subtle)", border: "1px solid var(--border)",
            }}>
              <div style={{
                width: 7, height: 7, borderRadius: "50%",
                background: connected ? "var(--success)" : "var(--danger)",
                boxShadow: connected ? "0 0 0 3px #22c55e20" : "none",
              }} />
              <span style={{ fontSize: 12, color: connected ? "var(--success)" : "var(--danger)", fontWeight: 500 }}>
                {connected ? "Live" : "Reconnecting"}
              </span>
            </div>

            <button
              onClick={() => navigate("/onboarding")}
              className="btn-secondary"
              style={{ fontSize: 13, padding: "6px 14px" }}
            >
              ⚙ Integrations
            </button>

            <button onClick={toggle} style={{
              background: "var(--bg-subtle)", border: "1px solid var(--border)",
              borderRadius: 8, width: 34, height: 34, cursor: "pointer",
              fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              {theme === "dark" ? "☀️" : "🌙"}
            </button>

            {email && (
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  width: 30, height: 30, borderRadius: "50%",
                  background: "var(--accent-subtle)", border: "1px solid var(--accent-border)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 13, fontWeight: 600, color: "var(--accent)",
                }}>
                  {email[0].toUpperCase()}
                </div>
                <button onClick={logout} style={{
                  background: "none", border: "none", color: "var(--text-muted)",
                  fontSize: 13, cursor: "pointer",
                }}>Sign out</button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Content */}
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "28px 24px" }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>
            Incident Feed
          </h1>
          <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
            Live agent reasoning traces — newest first
          </p>
        </div>

        <StatsBar incidents={incidents} />

        <div style={{ marginTop: 20 }}>
          {incidents.length === 0 ? (
            <div className="card" style={{ textAlign: "center", padding: "64px 24px" }}>
              <div style={{ fontSize: 40, marginBottom: 14 }}>⏳</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                No incidents yet
              </div>
              <div style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 24 }}>
                Make sure the simulator and detector are running,<br />
                or connect Prometheus to monitor real services.
              </div>
              <button
                onClick={() => navigate("/onboarding")}
                className="btn-primary"
                style={{ fontSize: 14, padding: "10px 22px" }}
              >
                Connect integrations →
              </button>
            </div>
          ) : (
            incidents.map((i) => <IncidentCard key={i.trace_id} incident={i} />)
          )}
        </div>
      </div>
    </div>
  );
}