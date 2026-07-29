import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import Signup from "./pages/Signup.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import ApplicationGate from "./components/ApplicationGate.jsx";
import Applications from "./pages/Applications.jsx";

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
        <Route path="/login" element={<Login />} />
         <Route element={<ProtectedRoute />}>
          <Route path="/applications" element={<Applications />} />
          <Route element={<ApplicationGate />}>
            <Route path="/onboarding" element={<Onboarding />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Route>
         </Route>
      
  
      </Routes>
    </BrowserRouter>
  );
}
