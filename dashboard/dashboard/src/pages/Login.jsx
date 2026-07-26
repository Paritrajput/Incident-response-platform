import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { notify } from "../utils/notify";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const validate = () => {
    if (!form.email.trim()) {
      notify.error("Email is required.");
      return false;
    }

    if (!/\S+@\S+\.\S+/.test(form.email)) {
      notify.error("Please enter a valid email address.");
      return false;
    }

    if (!form.password) {
      notify.error("Password is required.");
      return false;
    }

    return true;
  };

  const handleLogin = async (e) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);

    try {
      const data = await login(form.email, form.password);
    

      notify.success(`Welcome back, ${data.username}!`);

      navigate("/dashboard", {
        replace: true,
      });
    } catch (err) {
      notify.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-base)" }}>
      <Navbar showLinks={false} />

      <div className="flex min-h-[calc(100vh-60px)] items-center justify-center px-6 py-10">
        <div
          className="w-full max-w-md rounded-2xl border p-8 shadow-lg"
          style={{
            background: "var(--bg-surface)",
            borderColor: "var(--border)",
          }}
        >
          <div className="mb-8 text-center">
            <h1
              className="text-2xl font-bold"
              style={{ color: "var(--text-primary)" }}
            >
              Welcome Back
            </h1>

            <p
              className="mt-2 text-sm"
              style={{ color: "var(--text-secondary)" }}
            >
              Sign in to continue to your dashboard.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label
                className="mb-2 block text-sm font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                Email
              </label>

              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                className="input w-full"
                required
              />
            </div>

            <div>
              <label
                className="mb-2 block text-sm font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                Password
              </label>

              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                placeholder="Enter your password"
                className="input w-full"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Signing In..." : "Sign In"}
            </button>
          </form>

          <div
            className="mt-8 border-t pt-5 text-center"
            style={{ borderColor: "var(--border)" }}
          >
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Don't have an account?{" "}
              <Link
                to="/signup"
                className="font-semibold transition-colors hover:underline"
                style={{ color: "var(--accent)" }}
              >
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
