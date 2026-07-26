import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CgProfile } from "react-icons/cg";

import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../context/AuthContext";
import ProfileModal from "./ui/ProfileModal";

export default function Navbar({ showLinks = true }) {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  

 const {
    user,
    logout,
    isAuthenticated,
} = useAuth();
  const [showProfileModal, setShowProfileModal] = useState(false);



const handleLogout = async () => {
    await logout();

    setShowProfileModal(false);

    navigate("/", {
        replace: true,
    });
};

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        background: "var(--bg-base)",
        borderBottom: "1px solid var(--border)",
        backdropFilter: "blur(8px)",
      }}
    >
      <div
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 60,
        }}
      >
        {/* Logo */}
        <Link
          to="/"
          style={{
            textDecoration: "none",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                background: "var(--accent)",
                borderRadius: 8,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
              }}
            >
              ⚡
            </div>

            <span
              style={{
                fontSize: 16,
                fontWeight: 700,
                color: "var(--text-primary)",
              }}
            >
              IncidentAI
            </span>
          </div>
        </Link>

        {/* Right Section */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          {showLinks && (
            <>
              <a
                href="#features"
                style={{
                  fontSize: 14,
                  color: "var(--text-secondary)",
                  textDecoration: "none",
                  padding: "6px 12px",
                  transition: "0.2s",
                }}
              >
                Features
              </a>

              <a
                href="#how-it-works"
                style={{
                  fontSize: 14,
                  color: "var(--text-secondary)",
                  textDecoration: "none",
                  padding: "6px 12px",
                  transition: "0.2s",
                }}
              >
                How it works
              </a>
            </>
          )}

          {/* Theme Toggle */}
          <button
            onClick={toggle}
            title="Toggle theme"
            style={{
              background: "var(--bg-subtle)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              width: 36,
              height: 36,
              cursor: "pointer",
              fontSize: 16,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>

          {isAuthenticated ? (
            <div
              style={{
                position: "relative",
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              <button
                onClick={() => navigate("/dashboard")}
                className="btn-primary"
                style={{
                  fontSize: 13,
                  padding: "7px 16px",
                }}
              >
                Dashboard →
              </button>

              <button
                onClick={() =>
                  setShowProfileModal((prev) => !prev)
                }
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: "50%",
                  border: "1px solid var(--border)",
                  background: "var(--bg-subtle)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--text-primary)",
                  transition: "0.2s",
                }}
              >
                <CgProfile size={22} />
              </button>

              <ProfileModal
                email={user?.email}
                username={user?.username}
                handleLogout={handleLogout}
                showProfileModal={showProfileModal}
                closeModal={() => setShowProfileModal(false)}
              />
            </div>
          ) : (
<div
    style={{
        display: "flex",
        gap: 10,
        alignItems: "center",
    }}
>
    <button
        onClick={() => navigate("/login")}
        className="btn-secondary"
        style={{
            fontSize: 13,
            padding: "7px 16px",
        }}
    >
        Login
    </button>

    <button
        onClick={() => navigate("/signup")}
        className="btn-primary"
        style={{
            fontSize: 13,
            padding: "7px 16px",
        }}
    >
        Get Started
    </button>
</div>
          )}
        </div>
      </div>
    </nav>
  );
}