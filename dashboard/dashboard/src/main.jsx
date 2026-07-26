import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import { Toaster } from "react-hot-toast";
import App from "./App.jsx";
import "./index.css";
import { AuthProvider } from "./context/AuthContext.jsx";

// Set initial theme before render to avoid flash
const saved = localStorage.getItem("theme") || "dark";
document.documentElement.setAttribute("data-theme", saved);

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ThemeProvider>
       <AuthProvider>
        <Toaster
        position="top-right"
        reverseOrder={false}
        gutter={10}
        toastOptions={{
          duration: 4000,

          style: {
            background: "var(--bg-base)",
            color: "var(--text-primary)",
            border: "1px solid var(--border)",
            borderRadius: "12px",
            boxShadow: "0 12px 32px rgba(0,0,0,0.15)",
            padding: "14px 18px",
          },

          success: {
            iconTheme: {
              primary: "#22c55e",
              secondary: "#fff",
            },
          },

          error: {
            iconTheme: {
              primary: "#ef4444",
              secondary: "#fff",
            },
          },
        }}
      />

      <App />
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>
);