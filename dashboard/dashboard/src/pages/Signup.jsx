import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import Navbar from "../components/Navbar.jsx";

const API = "http://localhost:8000";

export default function Signup() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [copied, setCopied] = useState(false);

  async function handleSignup(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || "Signup failed"); return; }
      localStorage.setItem("api_key", data.api_key);
      localStorage.setItem("email", email);
      setApiKey(data.api_key);
    } catch {
      setError("Could not reach the server. Is the orchestrator running?");
    } finally {
      setLoading(false);
    }
  }

  function copy() {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (apiKey) {
    return (
      <div style={{ background: "var(--bg-base)", minHeight: "100vh" }}>
        <Navbar showLinks={false} />
        <div style={centerStyle}>
          <div className="card" style={cardStyle}>
            <div style={{ textAlign: "center", marginBottom: 28 }}>
              <div style={{
                width: 56, height: 56, borderRadius: 16,
                background: "var(--accent-subtle)", border: "1px solid var(--accent-border)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 26, margin: "0 auto 16px",
              }}>🎉</div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
                Account created!
              </h2>
              <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
                Save your API key — it won't be shown again.
              </p>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label className="label">Your API key</label>
              <div style={{
                background: "var(--bg-subtle)", border: "1px solid var(--border)",
                borderRadius: 8, padding: "12px 14px",
                fontFamily: "monospace", fontSize: 12,
                color: "var(--accent)", wordBreak: "break-all",
                lineHeight: 1.6,
              }}>
                {apiKey}
              </div>
            </div>

            <button onClick={copy} className="btn-secondary" style={{ width: "100%", marginBottom: 10 }}>
              {copied ? "✓ Copied!" : "📋 Copy API key"}
            </button>
            <button onClick={() => navigate("/onboarding")} className="btn-primary" style={{ width: "100%" }}>
              Continue to setup →
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: "var(--bg-base)", minHeight: "100vh" }}>
      <Navbar showLinks={false} />
      <div style={centerStyle}>
        <div className="card" style={cardStyle}>
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
              Create your account
            </h1>
            <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
              Free to start. No credit card required.
            </p>
          </div>

          <form onSubmit={handleSignup}>
            <div style={{ marginBottom: 16 }}>
              <label className="label">Email address</label>
              <input
                className="input"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            {error && (
              <div style={{
                background: "#ef444415", border: "1px solid #ef444430",
                color: "var(--danger)", borderRadius: 8,
                padding: "10px 14px", fontSize: 13, marginBottom: 16,
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{ width: "100%", padding: "11px", fontSize: 15 }}
            >
              {loading ? "Creating account..." : "Create free account →"}
            </button>
          </form>

          <div style={{
            marginTop: 24, paddingTop: 20,
            borderTop: "1px solid var(--border)",
            textAlign: "center",
          }}>
            <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Already have an account?{" "}
              <span
                onClick={() => {
                  const key = prompt("Paste your API key:");
                  if (key) { localStorage.setItem("api_key", key); navigate("/dashboard"); }
                }}
                style={{ color: "var(--accent)", cursor: "pointer", fontWeight: 500 }}
              >
                Sign in with API key
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

const centerStyle = {
  display: "flex", alignItems: "center", justifyContent: "center",
  minHeight: "calc(100vh - 61px)", padding: 24,
};
const cardStyle = { width: "100%", maxWidth: 420, padding: "36px 32px" };                                                                                                                                                                                                                                                                                                                                                                       