import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import Signup from "./pages/Signup.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Dashboard from "./pages/Dashboard.jsx";

// Simple auth check - if api_key is in localStorage, user is logged in.
function PrivateRoute({ children }) {
  const apiKey = localStorage.getItem("api_key");
  return apiKey ? children : <Navigate to="/signup" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/onboarding" element={
          <PrivateRoute><Onboarding /></PrivateRoute>
        } />
        <Route path="/dashboard" element={
          <PrivateRoute><Dashboard /></PrivateRoute>
        } />
      </Routes>
    </BrowserRouter>
  );
}
