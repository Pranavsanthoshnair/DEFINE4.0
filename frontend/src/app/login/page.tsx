"use client";

/**
 * Login page — Member 4.
 * Route: /login  (active root: frontend/src/app/login/page.tsx)
 *
 * Uses authApi.login from the shared API client.
 * On success the JWT is stored by authApi.login (sessionStorage "veylo_token")
 * and the user is redirected to /overview.
 *
 * Import path: @/lib/api-client resolves to frontend/src/lib/api-client.ts
 * per tsconfig.json paths: { "@/*": ["./src/*"] }.
 */

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api-client";

export default function LoginPage() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError("Both email and password are required.");
      return;
    }

    setLoading(true);
    try {
      // authApi.login stores the JWT in sessionStorage automatically.
      await authApi.login(email.trim(), password);
      router.push("/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--white, #f5f4ef)",
        padding: "16px",
      }}
    >
      <div
        className="glass"
        style={{ width: "100%", maxWidth: 400, padding: "32px 28px" }}
      >
        {/* Logo / wordmark */}
        <p
          style={{
            font: "800 22px 'Manrope', sans-serif",
            letterSpacing: "-.04em",
            marginBottom: 6,
          }}
        >
          VEYLO
        </p>
        <p
          style={{
            font: "400 13px 'Manrope', sans-serif",
            color: "#5B6B7D",
            marginBottom: 28,
          }}
        >
          Sign in to your account
        </p>

        {/* Error banner */}
        {error && (
          <p
            style={{
              padding: "8px 12px",
              background: "rgba(220,50,50,.08)",
              border: "1px solid rgba(220,50,50,.25)",
              borderRadius: 6,
              color: "var(--red, #d63a3a)",
              font: "600 12px 'Manrope', sans-serif",
              marginBottom: 16,
            }}
          >
            {error}
          </p>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <label
            htmlFor="login-email"
            style={{
              display: "block",
              font: "700 12px 'Manrope', sans-serif",
              marginBottom: 14,
            }}
          >
            Email
            <input
              id="login-email"
              type="email"
              className="vfield"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              style={{ marginTop: 5, fontWeight: 400 }}
              required
            />
          </label>

          <label
            htmlFor="login-password"
            style={{
              display: "block",
              font: "700 12px 'Manrope', sans-serif",
              marginBottom: 20,
            }}
          >
            Password
            <input
              id="login-password"
              type="password"
              className="vfield"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              style={{ marginTop: 5, fontWeight: 400 }}
              required
            />
          </label>

          <button
            type="submit"
            className="vbtn vbtn-red"
            disabled={loading}
            style={{ width: "100%" }}
          >
            {loading ? "Signing in…" : "SIGN IN ↗"}
          </button>
        </form>

        <div className="pgf" style={{ marginTop: 28 }}>
          <span>VEYLO / LOGIN</span><i>✳</i>
        </div>
      </div>
    </div>
  );
}
