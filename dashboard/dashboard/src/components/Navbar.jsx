import { useNavigate, Link } from "react-router-dom";
import { useTheme } from "../context/ThemeContext.jsx";

export default function Navbar({ showLinks = true }) {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const apiKey = localStorage.getItem("api_key");

  return (
    <nav style={{
      position: "sticky", top: 0, zIndex: 100,
      background: "var(--bg-base)",
      borderBottom: "1px solid var(--border)",
      backdropFilter: "blur(8px)",
    }}>
      <div style={{
        maxWidth: 1100, margin: "0 auto",
        padding: "0 24px",
        display: "flex", alignItems: "center",
        justifyContent: "space-between",
        height: 60,
      }}>
        {/* Logo */}
        <Link to="/" style={{ textDecoration: "none" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              width: 28, height: 28,
              background: "var(--accent)",
              borderRadius: 8,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 14,
            }}>⚡</div>
            <span style={{
              fontSize: 16, fontWeight: 700,
              color: "var(--text-primary)",
            }}>
              IncidentAI
            </span>
          </div>
        </Link>

        {/* Right side */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {showLinks && (
            <>
              <a href="#features" style={{
                fontSize: 14, color: "var(--text-secondary)",
                textDecoration: "none", padding: "6px 12px",
              }}>Features</a>
              <a href="#how-it-works" style={{
                fontSize: 14, color: "var(--text-secondary)",
                textDecoration: "none", padding: "6px 12px",
              }}>How it works</a>
            </>
          )}

          {/* Theme toggle */}
          <button
            onClick={toggle}
            title="Toggle theme"
            style={{
              background: "var(--bg-subtle)",
              border: "1px solid var(--border)",
              borderRadius: 8, width: 36, height: 36,
              cursor: "pointer", fontSize: 16,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>

          {/* CTA */}
          {apiKey ? (
            <button
              onClick={() => navigate("/dashboard")}
              className="btn-primary"
              style={{ fontSize: 13, padding: "7px 16px" }}
            >
              Dashboard →
            </button>
          ) : (
            <button
              onClick={() => navigate("/signup")}
              className="btn-primary"
              style={{ fontSize: 13, padding: "7px 16px" }}
            >
              Get started free
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}