const AGENTS = {
  log_analyst:       { label: "Log Analyst",      icon: "📋", color: "#6366f1" },
  deploy_correlator: { label: "Deploy Correlator", icon: "🚀", color: "#06b6d4" },
  metrics_analyst:   { label: "Metrics Analyst",   icon: "📊", color: "#8b5cf6" },
};

const CONF_COLOR = {
  high: "var(--success)", medium: "var(--warning)",
  low: "var(--danger)", none: "var(--text-muted)",
};

const agentKey = (s) => (s || "").split(".").pop();

export default function AgentResult({ result }) {
  const key = agentKey(result.agent);
  const meta = AGENTS[key] ?? { label: key, icon: "🤖", color: "var(--text-muted)" };
  const diag = result.diagnosis ?? {};
  const conf = diag.confidence ?? "none";

  return (
    <div style={{
      background: "var(--bg-subtle)",
      border: `1px solid ${meta.color}28`,
      borderTop: `2px solid ${meta.color}`,
      borderRadius: 10, padding: "14px 16px",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <span>{meta.icon}</span>
          <span style={{ fontSize: 13, fontWeight: 600, color: meta.color }}>{meta.label}</span>
        </div>
        <span style={{ fontSize: 11, fontWeight: 600, color: CONF_COLOR[conf] }}>{conf}</span>
      </div>

      <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.55, marginBottom: 10 }}>
        {diag.root_cause ?? "—"}
      </p>

      {diag.evidence?.length > 0 && (
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10 }}>
          {diag.evidence.map((e, i) => (
            <p key={i} style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 3 }}>• {e}</p>
          ))}
        </div>
      )}

      {result.deploy_count_found !== undefined && (
        <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8 }}>
          Deploys found: <strong style={{ color: "var(--text-secondary)" }}>{result.deploy_count_found}</strong>
        </p>
      )}
      {result.pre_classified_severity && (
        <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
          Severity: <strong style={{ color: "var(--text-secondary)" }}>{result.pre_classified_severity}</strong>
        </p>
      )}
      {result.error && (
        <div style={{
          marginTop: 8, fontSize: 11, color: "var(--danger)",
          background: "#ef444410", border: "1px solid #ef444428",
          borderRadius: 6, padding: "6px 10px",
        }}>
          ⚠ {result.error.slice(0, 80)}
        </div>
      )}
    </div>
  );
}