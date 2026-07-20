import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar.jsx";

const FEATURES = [
  { icon: "⚡", title: "Detects in seconds", desc: "Sliding-window anomaly detection on your Prometheus metrics. Catches spikes within 5 seconds, not 5 minutes." },
  { icon: "🤖", title: "3 independent agents", desc: "Log Analyst, Deploy Correlator, and Metrics Analyst run concurrently. Each brings independent signal — no groupthink." },
  { icon: "💬", title: "Slack-first alerts", desc: "Root cause lands in Slack before you open a dashboard. Know what broke and why, not just that something broke." },
  { icon: "🔍", title: "Full reasoning trace", desc: "See exactly what each agent found. No black box — every diagnosis comes with evidence and a recommended action." },
  { icon: "📊", title: "Real metrics", desc: "Connect your Prometheus instance in 30 seconds. Your real services, your real error rates, your real incidents." },
  { icon: "🚀", title: "Deploy correlation", desc: "GitHub webhook tracks every push. Bad deploy at 2:00pm, error spike at 2:01pm — we connect the dots automatically." },
];

const STEPS = [
  { n: "1", title: "Connect your stack", desc: "Paste your Prometheus URL, add a GitHub webhook, link a Slack channel. Under 5 minutes." },
  { n: "2", title: "We watch 24/7", desc: "Sliding-window anomaly detection monitors your services continuously and detects issues within seconds." },
  { n: "3", title: "Get the diagnosis", desc: "Three AI agents diagnose the incident in parallel. You get root cause + recommended action in Slack." },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div style={{ background: "var(--bg-base)", minHeight: "100vh" }}>
      <Navbar />

      {/* Hero */}
      <section style={{ maxWidth: 800, margin: "0 auto", padding: "88px 24px 72px", textAlign: "center" }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          background: "var(--accent-subtle)", border: "1px solid var(--accent-border)",
          color: "var(--accent)", borderRadius: 20,
          padding: "5px 14px", fontSize: 13, fontWeight: 500, marginBottom: 28,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)", display: "inline-block" }} />
          Real-time multi-agent incident diagnosis
        </div>

        <h1 style={{
          fontSize: "clamp(36px, 5vw, 56px)",
          fontWeight: 800, lineHeight: 1.1,
          letterSpacing: "-0.02em",
          color: "var(--text-primary)", marginBottom: 24,
        }}>
          Know <em style={{ color: "var(--accent)", fontStyle: "normal" }}>why</em> your service broke<br />
          before you open a dashboard
        </h1>

        <p style={{
          fontSize: 18, color: "var(--text-secondary)",
          lineHeight: 1.7, maxWidth: 540, margin: "0 auto 40px",
        }}>
          IncidentAI detects anomalies in your metrics, runs three independent AI agents
          to find the root cause, and delivers the answer to Slack — in under 30 seconds.
        </p>

        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <button
            onClick={() => navigate("/signup")}
            className="btn-primary"
            style={{ fontSize: 15, padding: "12px 28px" }}
          >
            Start for free →
          </button>
          <a
            href="#how-it-works"
            className="btn-secondary"
            style={{ fontSize: 15, padding: "12px 28px", display: "inline-block" }}
          >
            See how it works
          </a>
        </div>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 20 }}>
          No credit card · Free tier · Setup in 5 minutes
        </p>
      </section>

      {/* Mock Slack message */}
      <section style={{ maxWidth: 560, margin: "0 auto 96px", padding: "0 24px" }}>
        <div className="card" style={{ padding: 24, background: "var(--bg-subtle)" }}>
          {/* Slack chrome */}
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            marginBottom: 14, paddingBottom: 14,
            borderBottom: "1px solid var(--border)",
          }}>
            <div style={{
              width: 10, height: 10, borderRadius: "50%", background: "#ef4444",
              boxShadow: "0 0 0 3px #ef444420",
            }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>
              # incidents — Slack
            </span>
          </div>

          <div style={{ display: "flex", gap: 12 }}>
            <div style={{
              width: 36, height: 36, background: "var(--accent)",
              borderRadius: 8, flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18,
            }}>⚡</div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 10 }}>
                <span style={{ fontWeight: 700, fontSize: 14, color: "var(--text-primary)" }}>IncidentAI</span>
                <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Today at 2:03 PM</span>
              </div>
              <div style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderLeft: "3px solid var(--danger)",
                borderRadius: 8, padding: "14px 16px",
              }}>
                <div style={{ fontWeight: 700, fontSize: 14, color: "var(--danger)", marginBottom: 10 }}>
                  🔴 Incident — payment-service
                </div>
                <Row label="Root cause" value="Bad deploy d4f9a2 caused connection pool exhaustion — 22% error rate." />
                <Row label="Confidence" value="High ✓" color="var(--success)" />
                <Row label="Action" value="Roll back deploy d4f9a2 immediately" />
                <div style={{ marginTop: 12 }}>
                  <div style={{
                    display: "inline-block", background: "var(--accent)",
                    color: "#fff", fontSize: 12, fontWeight: 600,
                    padding: "6px 14px", borderRadius: 6, cursor: "pointer",
                  }}>
                    View full trace →
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <p style={{ textAlign: "center", fontSize: 13, color: "var(--text-muted)", marginTop: 12 }}>
          Root cause in Slack. No dashboard required.
        </p>
      </section>

      {/* Features */}
      <section id="features" style={{ maxWidth: 1060, margin: "0 auto 96px", padding: "0 24px" }}>
        <SectionHeader
          title="Everything you need to debug faster"
          sub="Built on real distributed systems — Kafka, async Python, and independent AI agents."
        />
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: 16, marginTop: 48,
        }}>
          {FEATURES.map((f) => (
            <div key={f.title} className="card" style={{ padding: "24px 22px" }}>
              <div style={{ fontSize: 26, marginBottom: 14 }}>{f.icon}</div>
              <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)", marginBottom: 8 }}>
                {f.title}
              </div>
              <div style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.65 }}>
                {f.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" style={{ maxWidth: 700, margin: "0 auto 96px", padding: "0 24px" }}>
        <SectionHeader
          title="Up and running in 5 minutes"
          sub="No agents to install. No config files to write."
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 48 }}>
          {STEPS.map((s) => (
            <div key={s.n} className="card" style={{
              display: "flex", gap: 20, padding: "22px 24px", alignItems: "flex-start",
            }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                background: "var(--accent-subtle)", border: "1px solid var(--accent-border)",
                color: "var(--accent)", fontWeight: 800, fontSize: 14,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                {s.n}
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)", marginBottom: 4 }}>
                  {s.title}
                </div>
                <div style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  {s.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={{
        background: "var(--bg-subtle)", borderTop: "1px solid var(--border)",
        padding: "80px 24px", textAlign: "center",
      }}>
        <h2 style={{ fontSize: 34, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--text-primary)", marginBottom: 14 }}>
          Ready to stop firefighting?
        </h2>
        <p style={{ fontSize: 16, color: "var(--text-secondary)", marginBottom: 32 }}>
          Free to start. Connect your first integration in under 5 minutes.
        </p>
        <button
          onClick={() => navigate("/signup")}
          className="btn-primary"
          style={{ fontSize: 15, padding: "13px 32px" }}
        >
          Create free account →
        </button>
      </section>

      <footer style={{
        borderTop: "1px solid var(--border)", padding: "24px",
        textAlign: "center", fontSize: 13, color: "var(--text-muted)",
      }}>
        ⚡ IncidentAI — Built with Kafka · Python asyncio · Gemini · React
      </footer>
    </div>
  );
}

function Row({ label, value, color }) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 6, fontSize: 13 }}>
      <span style={{ color: "var(--text-muted)", minWidth: 80 }}>{label}:</span>
      <span style={{ color: color || "var(--text-primary)", fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function SectionHeader({ title, sub }) {
  return (
    <div style={{ textAlign: "center" }}>
      <h2 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--text-primary)", marginBottom: 10 }}>
        {title}
      </h2>
      <p style={{ fontSize: 16, color: "var(--text-secondary)" }}>{sub}</p>
    </div>
  );
}