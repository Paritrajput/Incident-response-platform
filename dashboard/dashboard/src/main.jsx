import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import App from "./App.jsx";
import "./index.css";

// Set initial theme before render to avoid flash
const saved = localStorage.getItem("theme") || "dark";
document.documentElement.setAttribute("data-theme", saved);

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>
);