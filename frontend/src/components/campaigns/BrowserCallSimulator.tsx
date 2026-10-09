"use client";

/**
 * BrowserCallSimulator
 * ────────────────────
 * Full browser-based outbound call simulation:
 *  1. Fetches pre-generated ElevenLabs audio from backend (/api/v1/audio/{token})
 *  2. Plays the AI greeting through the browser speaker
 *  3. Records the user's response via microphone (MediaRecorder)
 *  4. Sends the audio blob to backend /api/v1/sessions/stt for transcription
 *  5. Sends transcript to /api/v1/sessions/classify for intent
 *  6. Shows result and plays acknowledgement audio
 *  7. Updates campaign execution session in real-time
 */

import React, { useCallback, useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Phase =
  | "idle"
  | "loading"
  | "greeting"      // AI speaking greeting
  | "listening"     // recording user
  | "processing"    // STT + intent
  | "responding"    // AI speaking response
  | "done"
  | "error";

interface SimResult {
  transcript: string;
  intent: string;
  confidence: number | null;
  method: string;
  response_text: string;
}

interface Props {
  campaignId: string;
  contactName?: string;
  language?: string;
  onComplete?: (result: SimResult) => void;
}

export default function BrowserCallSimulator({
  campaignId,
  contactName = "Participant",
  language = "en",
  onComplete,
}: Props) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Timer ──────────────────────────────────────────────────────────────────
  const startTimer = () => {
    setElapsedMs(0);
    timerRef.current = setInterval(() => setElapsedMs((t) => t + 100), 100);
  };
  const stopTimer = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  };

  useEffect(() => () => stopTimer(), []);

  // ── Play audio URL in browser ──────────────────────────────────────────────
  const playAudio = useCallback((url: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => resolve();
      audio.onerror = () => reject(new Error("Audio playback failed"));
      audio.play().catch(reject);
    });
  }, []);

  // ── Step 1: Create session + play greeting ─────────────────────────────────
  const startCall = useCallback(async () => {
    setPhase("loading");
    setError(null);
    setResult(null);
    setTranscript("");

    try {
      // Create execution session
      const sessionRes = await fetch(`${API}/api/v1/sessions/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ campaign_id: campaignId, channel: "browser", language }),
      });
      if (!sessionRes.ok) throw new Error(`Session error: ${sessionRes.status}`);
      const session = await sessionRes.json();
      setSessionId(session.session_id ?? session.id ?? null);

      // Fetch greeting audio token
      const audioRes = await fetch(`${API}/api/v1/campaigns/${campaignId}/audio-token?segment=greeting`);
      if (!audioRes.ok) throw new Error("Could not get audio token");
      const { token } = await audioRes.json();

      setPhase("greeting");
      startTimer();
      await playAudio(`${API}/api/v1/audio/${token}`);
      stopTimer();

      // Move to listening
      await startRecording();
    } catch (err) {
      stopTimer();
      setError(err instanceof Error ? err.message : "Call failed");
      setPhase("error");
    }
  }, [campaignId, language, playAudio]);

  // ── Step 2: Record microphone ──────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    setPhase("listening");
    chunksRef.current = [];
    startTimer();

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mr = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
    mediaRecorderRef.current = mr;

    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    mr.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      stopTimer();
      await processRecording();
    };

    mr.start();
    // Auto-stop after 8 seconds
    setTimeout(() => {
      if (mr.state === "recording") mr.stop();
    }, 8000);
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  // ── Step 3: STT + intent ───────────────────────────────────────────────────
  const processRecording = useCallback(async () => {
    setPhase("processing");
    startTimer();

    try {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const form = new FormData();
      form.append("audio", blob, "response.webm");
      form.append("language", language);
      if (sessionId) form.append("session_id", sessionId);

      // STT
      const sttRes = await fetch(`${API}/api/v1/sessions/stt`, { method: "POST", body: form });
      if (!sttRes.ok) throw new Error(`STT failed: ${sttRes.status}`);
      const sttData = await sttRes.json();
      const text: string = sttData.transcript ?? sttData.text ?? "";
      setTranscript(text);

      // Intent classification
      const intentRes = await fetch(`${API}/api/v1/sessions/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, language, session_id: sessionId }),
      });
      if (!intentRes.ok) throw new Error(`Intent failed: ${intentRes.status}`);
      const intentData = await intentRes.json();

      stopTimer();

      const simResult: SimResult = {
        transcript: text,
        intent: intentData.intent,
        confidence: intentData.confidence ?? null,
        method: intentData.method ?? "unknown",
        response_text: intentData.response_text ?? INTENT_RESPONSES[intentData.intent] ?? "Thank you.",
      };
      setResult(simResult);

      // Play response audio
      setPhase("responding");
      try {
        const ackRes = await fetch(`${API}/api/v1/campaigns/${campaignId}/audio-token?segment=${intentData.intent}`);
        if (ackRes.ok) {
          const { token } = await ackRes.json();
          await playAudio(`${API}/api/v1/audio/${token}`);
        }
      } catch {
        // Silent fallback — use browser TTS
        const msg = new SpeechSynthesisUtterance(simResult.response_text);
        msg.lang = language;
        window.speechSynthesis.speak(msg);
        await new Promise<void>((r) => { msg.onend = () => r(); setTimeout(r, 5000); });
      }

      setPhase("done");
      onComplete?.(simResult);
    } catch (err) {
      stopTimer();
      setError(err instanceof Error ? err.message : "Processing failed");
      setPhase("error");
    }
  }, [campaignId, language, sessionId, playAudio, onComplete]);

  // ── Render ─────────────────────────────────────────────────────────────────
  const PHASE_LABELS: Record<Phase, string> = {
    idle: "Ready to simulate call",
    loading: "Setting up call…",
    greeting: "🔊 AI is speaking…",
    listening: "🎙 Recording your response…",
    processing: "🧠 Analysing intent…",
    responding: "🔊 AI is responding…",
    done: "✅ Call complete",
    error: "❌ Call failed",
  };

  const INTENT_COLORS: Record<string, string> = {
    confirm: "#22c55e",
    decline: "#ef4444",
    call_later: "#f59e0b",
    reschedule: "#8b5cf6",
    stop_calling: "#6b7280",
    unclear: "#64748b",
  };

  return (
    <div
      style={{
        background: "rgba(255,253,248,.9)",
        border: "1.5px solid rgba(23,38,58,.1)",
        borderRadius: 16,
        padding: "20px 24px",
        fontFamily: "Manrope, sans-serif",
        maxWidth: 520,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <div
          style={{
            width: 44, height: 44, borderRadius: "50%",
            background: phase === "idle" || phase === "done" ? "#17263A" : "#EA1D2C",
            display: "grid", placeItems: "center",
            animation: ["greeting", "responding"].includes(phase) ? "pulseRing 1.5s infinite" : "none",
          }}
        >
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.15 12 19.79 19.79 0 0 1 1.07 3.38 2 2 0 0 1 3 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.09 8.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21 16z"/>
          </svg>
        </div>
        <div>
          <p style={{ margin: 0, fontWeight: 800, fontSize: 15, color: "#17263A" }}>Browser Call Simulator</p>
          <p style={{ margin: 0, fontSize: 12, color: "#5A6E84" }}>Calling: {contactName} · ElevenLabs voice</p>
        </div>
        {phase !== "idle" && phase !== "done" && phase !== "error" && (
          <div style={{ marginLeft: "auto", fontSize: 12, color: "#8A9BB0", fontVariantNumeric: "tabular-nums" }}>
            {(elapsedMs / 1000).toFixed(1)}s
          </div>
        )}
      </div>

      {/* Status */}
      <div style={{ background: "rgba(23,38,58,.04)", borderRadius: 10, padding: "10px 14px", marginBottom: 14 }}>
        <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "#17263A" }}>{PHASE_LABELS[phase]}</p>
        {transcript && (
          <p style={{ margin: "6px 0 0", fontSize: 12, color: "#4A5B6E", fontStyle: "italic" }}>
            "{transcript}"
          </p>
        )}
      </div>

      {/* Result card */}
      {result && (
        <div style={{ border: `2px solid ${INTENT_COLORS[result.intent] ?? "#64748b"}`, borderRadius: 10, padding: "12px 16px", marginBottom: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontWeight: 800, fontSize: 14, color: INTENT_COLORS[result.intent] ?? "#64748b", textTransform: "uppercase", letterSpacing: ".06em" }}>
              {result.intent}
            </span>
            <span style={{ fontSize: 11, color: "#8A9BB0" }}>
              {result.confidence != null ? `${(result.confidence * 100).toFixed(0)}% confidence` : ""} · {result.method}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: "#33465C" }}>{result.response_text}</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 8, padding: "10px 14px", marginBottom: 12, fontSize: 13, color: "#dc2626" }}>
          {error}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {(phase === "idle" || phase === "done" || phase === "error") && (
          <button
            onClick={startCall}
            style={{
              background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 8,
              padding: "10px 20px", fontFamily: "Manrope, sans-serif", fontWeight: 700,
              fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 8,
            }}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/></svg>
            {phase === "idle" ? "Start Call" : "Try Again"}
          </button>
        )}

        {phase === "listening" && (
          <button
            onClick={stopRecording}
            style={{
              background: "#17263A", color: "#fff", border: "none", borderRadius: 8,
              padding: "10px 20px", fontFamily: "Manrope, sans-serif", fontWeight: 700,
              fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 8,
            }}
          >
            <span style={{ width: 10, height: 10, background: "#EA1D2C", borderRadius: 2, display: "inline-block" }} />
            Stop Recording
          </button>
        )}

        {phase !== "idle" && phase !== "loading" && (
          <button
            onClick={() => {
              audioRef.current?.pause();
              mediaRecorderRef.current?.stop();
              stopTimer();
              setPhase("idle");
            }}
            style={{
              background: "transparent", color: "#5A6E84", border: "1.5px solid rgba(23,38,58,.15)",
              borderRadius: 8, padding: "10px 16px", fontFamily: "Manrope, sans-serif",
              fontWeight: 600, fontSize: 13, cursor: "pointer",
            }}
          >
            End Call
          </button>
        )}
      </div>
    </div>
  );
}

const INTENT_RESPONSES: Record<string, string> = {
  confirm: "✅ Thank you for confirming! We look forward to seeing you.",
  decline: "❌ Understood, thank you for letting us know.",
  call_later: "📞 We'll call you back at a more convenient time.",
  reschedule: "🔄 We'll follow up with rescheduling options.",
  stop_calling: "🛑 You've been removed from our call list.",
  unclear: "🤔 Sorry, we didn't catch that. Please try again.",
};
