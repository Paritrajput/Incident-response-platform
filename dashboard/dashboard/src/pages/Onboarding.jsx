import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar.jsx";

import { applicationsApi } from "../services/api";
import { useApplications } from "../context/ApplicationContext";

const STEPS = [
  {
    id: "slack", icon: "💬", title: "Connect Slack", required: true,
    subtitle: "Get incident alerts delivered directly to your team channel.",
    fields: [
      { key: "bot_token", label: "Bot Token", placeholder: "xoxb-...", type: "password", hint: "api.slack.com/apps → OAuth & Permissions → Bot User OAuth Token" },
      { key: "channel_id", label: "Channel ID", placeholder: "C0BGM4Z8HS4", type: "text", hint: "Right-click channel → View channel details → ID at the bottom" },
    ],
  },
  {
    id: "prometheus", icon: "📊", title: "Connect Prometheus", required: false,
    subtitle: "Monitor real services instead of synthetic data.",
    fields: [
      { key: "prometheus_url", label: "Prometheus URL", placeholder: "http://localhost:9090", type: "text", hint: "The base URL of your Prometheus instance. Try Docker: docker run -d -p 9090:9090 prom/prometheus" },
    ],
  },
  {
    id: "github", icon: "🚀", title: "Connect GitHub", required: false,
    subtitle: "Correlate incidents with deploys automatically.",
    fields: [
      { key: "webhook_secret", label: "Webhook Secret", placeholder: "any-secret-string", type: "password", hint: "Choose any string — use the same value in your GitHub webhook settings" },
    ],
  },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const { selectedApplication } = useApplications();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(new Set());

  useEffect(() => {
    if (!selectedApplication) return;
    applicationsApi.integrations(selectedApplication.id)
      .then((integrations) => {
        const configured = new Set(integrations.map((integration) => integration.type));
        setDone(configured);
      })
      .catch(() => setDone(new Set()));
  }, [selectedApplication?.id]);

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

async function connect() {
  setLoading(true);
  setError("");

  const payload = Object.fromEntries(
    current.fields.map((field) => [
      field.key,
      form[`${current.id}_${field.key}`] || "",
    ])
  );

  try {
    await applicationsApi.connectIntegration(selectedApplication.id, current.id, payload);

    setDone((prev) => {
      const next = new Set(prev);
      next.add(current.id);
      return next;
    });

    next();
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

  function next() {
    if (isLast) navigate("/dashboard");
    else { setStep((s) => s + 1); setError(""); }
  }

  if (!selectedApplication) return null;

  return (
    <div style={{ background: "var(--bg-base)", minHeight: "100vh" }}>
      <Navbar showLinks={false} />
      <div style={{ maxWidth: 540, margin: "0 auto", padding: "48px 24px" }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
            Set up your integrations
          </h1>
          <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
            Connect tools for <strong>{selectedApplication.name}</strong> so IncidentAI can monitor and notify you.
          </p>
        </div>

        {/* Progress */}
        <div style={{ display: "flex", gap: 6, marginBottom: 32, justifyContent: "center" }}>
          {STEPS.map((s, i) => (
            <div key={s.id} style={{
              height: 4, borderRadius: 4,
              width: i === step ? 32 : 16,
              background: done.has(s.id) ? "var(--success)" : i === step ? "var(--accent)" : "var(--border)",
              transition: "all 0.3s",
            }} />
          ))}
        </div>

        {/* Card */}
        <div className="card" style={{ padding: "32px 28px" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{
                width: 44, height: 44, borderRadius: 10,
                background: "var(--accent-subtle)", border: "1px solid var(--accent-border)",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22,
              }}>
                {current.icon}
              </div>
              <div>
                <h2 style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>
                  {current.title}
                </h2>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                  {current.subtitle}
                </p>
              </div>
            </div>
            {!current.required && (
              <span style={{
                fontSize: 11, color: "var(--text-muted)",
                background: "var(--bg-subtle)", border: "1px solid var(--border)",
                borderRadius: 4, padding: "3px 8px", whiteSpace: "nowrap",
              }}>optional</span>
            )}
          </div>

          <div style={{ height: 1, background: "var(--border)", margin: "0 0 22px" }} />

          {current.fields.map((field) => (
            <div key={field.key} style={{ marginBottom: 18 }}>
              <label className="label">{field.label}</label>
              <input
                className="input"
                type={field.type}
                placeholder={field.placeholder}
                value={form[`${current.id}_${field.key}`] || ""}
                onChange={(e) => setForm((p) => ({ ...p, [`${current.id}_${field.key}`]: e.target.value }))}
              />
              {field.hint && (
                <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 5, lineHeight: 1.5 }}>
                  💡 {field.hint}
                </p>
              )}
            </div>
          ))}

          {current.id === "github" && (
            <div style={{
              background: "var(--bg-subtle)", border: "1px solid var(--border)",
              borderRadius: 8, padding: "12px 14px", marginBottom: 18,
            }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                After connecting, add this webhook in GitHub:
              </p>
              <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
                Repo → Settings → Webhooks → Add webhook
              </p>
              <p style={{ fontSize: 12, fontFamily: "monospace", color: "var(--accent)", marginTop: 4 }}>
                http://localhost:8000/webhooks/github
              </p>
            </div>
          )}

          {error && (
            <div style={{
              background: "#ef444415", border: "1px solid #ef444430",
              color: "var(--danger)", borderRadius: 8,
              padding: "10px 14px", fontSize: 13, marginBottom: 16,
            }}>{error}</div>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={connect} disabled={loading} className="btn-primary" style={{ flex: 1, padding: "11px" }}>
              {loading ? "Connecting..." : `Connect ${current.title.replace("Connect ", "")}`}
            </button>
            {!current.required && (
              <button onClick={next} className="btn-secondary" style={{ padding: "11px 20px" }}>
                Skip
              </button>
            )}
          </div>
        </div>

        <p style={{ textAlign: "center", fontSize: 13, color: "var(--text-muted)", marginTop: 16 }}>
          Step {step + 1} of {STEPS.length}
        </p>
      </div>
    </div>
  );
}
