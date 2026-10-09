"use client";

import React from "react";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches render-time and async errors in the (app) layout tree.
 * Prevents a single failing page from crashing the entire shell.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Log to console in dev; swap for a real error-tracking SDK in production
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "60vh",
            gap: 16,
            color: "var(--muted, #64748b)",
            fontFamily: "Inter, sans-serif",
          }}
        >
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: "var(--foreground, #0f172a)" }}>
            Something went wrong
          </h2>
          <p style={{ fontSize: 14, maxWidth: 360, textAlign: "center" }}>
            {this.state.error?.message ?? "An unexpected error occurred on this page."}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "1px solid var(--border, #e2e8f0)",
              background: "var(--background, #fff)",
              cursor: "pointer",
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            Reload page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
