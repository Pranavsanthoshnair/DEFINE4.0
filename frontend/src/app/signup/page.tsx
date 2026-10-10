"use client";

/**
 * Signup page — Member 4.
 * Route: /signup (frontend/src/app/signup/page.tsx)
 *
 * Uses authApi.signup from the shared API client.
 * On success the JWT is stored by authApi.signup (sessionStorage "veylo_token")
 * and the user is redirected to /overview.
 */

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api-client";

export default function SignupPage() {
  const [email, setEmail]             = useState("");
  const [password, setPassword]       = useState("");
  const [confirmPass, setConfirmPass] = useState("");
  const [error, setError]             = useState<string | null>(null);
  const [loading, setLoading]         = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !password) {
      setError("Email and password are required.");
      return;
    }

    if (!cleanEmail.includes("@") || !cleanEmail.includes(".")) {
      setError("Please enter a valid email address.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPass) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      // authApi.signup registers user and stores the JWT in sessionStorage
      await authApi.signup(cleanEmail, password);
      router.push("/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed. Please try again.");
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
        style={{ width: "100%", maxWidth: 420, padding: "34px 30px" }}
      >
        {/* Logo / wordmark */}
        <Link href="/" style={{ textDecoration: "none", display: "inline-block" }}>
          <p
            style={{
              font: "800 24px 'Manrope', sans-serif",
              letterSpacing: "-.04em",
              marginBottom: 4,
              color: "inherit",
            }}
          >
            VEY<span style={{ color: "var(--red, #d63a3a)" }}>LO</span>
          </p>
        </Link>
        <p
          style={{
            font: "400 13.5px 'Manrope', sans-serif",
            color: "#5B6B7D",
            marginBottom: 24,
          }}
        >
          Create your account to start campaigns
        </p>

        {/* Error banner */}
        {error && (
          <p
            style={{
              padding: "9px 12px",
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
            htmlFor="signup-email"
            style={{
              display: "block",
              font: "700 12px 'Manrope', sans-serif",
              marginBottom: 14,
            }}
          >
            Email Address
            <input
              id="signup-email"
              type="email"
              className="vfield"
              autoComplete="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              style={{ marginTop: 5, fontWeight: 400 }}
              required
            />
          </label>

          <label
            htmlFor="signup-password"
            style={{
              display: "block",
              font: "700 12px 'Manrope', sans-serif",
              marginBottom: 14,
            }}
          >
            Password
            <input
              id="signup-password"
              type="password"
              className="vfield"
              autoComplete="new-password"
              placeholder="Minimum 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              style={{ marginTop: 5, fontWeight: 400 }}
              required
            />
          </label>

          <label
            htmlFor="signup-confirm-password"
            style={{
              display: "block",
              font: "700 12px 'Manrope', sans-serif",
              marginBottom: 22,
            }}
          >
            Confirm Password
            <input
              id="signup-confirm-password"
              type="password"
              className="vfield"
              autoComplete="new-password"
              placeholder="Re-enter your password"
              value={confirmPass}
              onChange={(e) => setConfirmPass(e.target.value)}
              disabled={loading}
              style={{ marginTop: 5, fontWeight: 400 }}
              required
            />
          </label>

          <button
            type="submit"
            className="vbtn vbtn-red"
            disabled={loading}
            style={{ width: "100%", justifyContent: "center", marginBottom: 16 }}
          >
            {loading ? "Creating account…" : "CREATE ACCOUNT ↗"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: 14 }}>
          <span style={{ fontSize: 13, color: "#5B6B7D" }}>
            Already have an account?{" "}
          </span>
          <Link
            href="/login"
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "var(--red, #d63a3a)",
              textDecoration: "none",
            }}
          >
            Sign in ↗
          </Link>
        </div>

        <div className="pgf" style={{ marginTop: 26 }}>
          <span>VEYLO / REGISTER</span><i>✳</i>
        </div>
      </div>
    </div>
  );
}
