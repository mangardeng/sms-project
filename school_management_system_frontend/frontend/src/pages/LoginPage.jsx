import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { extractErrorMessage } from "../api/client";
import AlertBanner from "../components/AlertBanner";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const dashboardPath = await login(identifier, password);
      const redirectTo = location.state?.from?.pathname;
      navigate(redirectTo || dashboardPath, { replace: true });
    } catch (err) {
      setError(extractErrorMessage(err, "Invalid credentials. Please try again."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="brand-mark">Welcome To Bright Star Academy SMS</div>
        <div className="brand-sub">Sign in to your school account</div>

        <AlertBanner type="error">{error}</AlertBanner>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="identifier">Enter Username or student index number</label>
            <input
              id="identifier"
              type="text"
              autoComplete="username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder=" "
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? <span className="spinner" /> : null}
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

      </div>
    </div>
  );
}
