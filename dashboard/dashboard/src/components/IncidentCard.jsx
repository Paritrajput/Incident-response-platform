import { useState } from "react";
import AgentResult from "./AgentResult.jsx";

const CONF_STYLES = {
  high:   { color: "var(--success)", bg: "#22c55e12", border: "#22c55e25" },
  medium: { color: "var(--warning)", bg: "#f59e0b12", border: "#f59e0b25" },
  low:    { color: "var(--danger)",  bg: "#ef444412", border: "#ef444425" },
  none:   { color: "var(--text-muted)", bg: "var(--bg-subtle)", border: "var(--border)" },
};

const SVC_COLORS = ["#6366f1","#06b6d4","#8b5cf6","#ec4899","#f59e0b","#10b981"];
const svcColor = (s) => SVC_COLORS[(s || "").split("").reduce((a, c) => a + c.charCodeAt(0), 0) % SVC_COLORS.length];

function timeAgo(iso) {
  const d = Math.floor((Date.now() - new Date(iso)) / 1000);
  return d < 60 ? `${d}s ago` : `${Math.floor(d / 60)}m ago`;
}

export default function IncidentCard({ incident }) {
  const [open, setOpen] = useState(true);
  const final = incident.resolution?.final_diagnosis ?? {};
  const conf = final.confidence ?? "none";
  const cs = CONF_STYLES[conf] ?? CONF_STYLES.none;
  const sc = svcColor(incident.service);
  const disagree = incident.resolution?.disagreement_score ?? 0;

  return (
    <div className="card" style={{ marginBottom: 12, overflow: "hidden" }}>
      {/* Header row */}
      <div
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "14px 18px", cursor: "pointer",
          borderBottom: open ? "1px solid var(--border)" : "none",
        }}
      >
        {/* Service badge */}
        <span style={{
          background: sc + "18", border: `1px solid ${sc}35`,
          color: sc, borderRadius: 6,
          padding: "2px 10px", fontSize: 12, fontWeight: 600, whiteSpace: "nowrap",
        }}>
          {incident.service}
        </span>

        {/* Root cause */}
        <span style={{
          flex: 1, fontSize: 13, color: "var(--text-secondary)",
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>
          {final.root_cause ?? "Processing..."}
        </span>

        {/* Meta */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <span style={{
            fontSize: 11, fontWeight: 600, color: cs.color,
            background: cs.bg, border: `1px solid ${cs.border}`,
            borderRadius: 6, padding: "2px 8px",
          }}>
            {conf}
          </span>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{incident.latency_ms}ms</span>
          <span style={{ fontSize: 11, color: disagree > 0.6 ? "var(--warning)" : "var(--text-muted)" }}>
            Δ{disagree.toFixed(2)}
          </span>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {timeAgo(incident.timestamp)}
          </span>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{open ? "▲" : "▼"}</span>
        </div>
      </div>

      {/* Expanded body */}
      {open && (
        <div style={{ padding: "18px 18px 20px" }}>
          {/* Trace info */}
          <p style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-muted)", marginBottom: 16 }}>
            trace: {incident.trace_id} · {new Date(incident.incident_timestamp).toLocaleTimeString()}
          </p>

          {/* Final diagnosis */}
          <div style={{
            background: cs.bg, border: `1px solid ${cs.border}`,
            borderRadius: 10, padding: "16px 18px", marginBottom: 18,
          }}>
            <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.06em", marginBottom: 10 }}>
              RESOLVER — FINAL DIAGNOSIS
            </p>
            <p style={{ fontSize: 14, color: "var(--text-primary)", fontWeight: 500, marginBottom: 10, lineHeight: 1.6 }}>
              {final.root_cause}
            </p>
            <p style={{ fontSize: 13, color: cs.color, marginBottom: 12 }}>
              → {final.recommended_action}
            </p>
            {final.corroborating_evidence?.length > 0 && (
              <div style={{ borderTop: `1px solid ${cs.border}`, paddingTop: 10 }}>
                <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.05em", marginBottom: 6 }}>
                  CORROBORATED BY
                </p>
                {final.corroborating_evidence.map((e, i) => (
                  <p key={i} style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 3 }}>• {e}</p>
                ))}
              </div>
            )}
          </div>

          {/* Agent cards */}
          <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.06em", marginBottom: 12 }}>
            AGENT REASONING TRACES
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 10 }}>
            {incident.agent_results?.map((r, i) => <AgentResult key={i} result={r} />)}
          </div>
        </div>
      )}
    </div>
  );
}