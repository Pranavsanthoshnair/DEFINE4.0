"use client";

/**
 * BrowserCallSimulator — wired to the REAL backend API
 *
 * Flow (matching actual backend routes):
 *  1. POST /api/v1/sessions/browser/start      → creates session, returns {id, prompt_text}
 *  2. POST /api/v1/sessions/browser/{id}/tts   → returns MP3 bytes, play in browser
 *  3. MediaRecorder captures mic input
 *  4. POST /api/v1/sessions/browser/{id}/respond (multipart: audio file)
 *     → backend does STT → intent → returns {intent, transcript, confidence, response_text}
 *  5. Speaks response_text via browser SpeechSynthesis (no extra API call needed)
 */

import React, { useCallback, useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Phase =
  | "idle"
  | "starting"
  | "greeting"
  | "listening"
  | "processing"
  | "responding"
  | "done"
  | "error";

interface SessionOut {
  id: string;
  campaign_id: string;
  language: string;
  status: string;
  prompt_text?: string;
}

interface RespondResult {
  session_id: string;
  intent: string;
  transcript: string | null;
  language: string;
  confidence: number | null;
  decision_method: string;
  response_text: string;
  error?: string | null;
}

interface Props {
  campaignId: string;
  language?: string;
  onComplete?: (result: RespondResult) => void;
}

const INTENT_COLOR: Record<string, string> = {
  confirm:       "#16a34a",
  decline:       "#dc2626",
  call_later:    "#d97706",
  reschedule:    "#7c3aed",
  stop_calling:  "#6b7280",
  unclear:       "#64748b",
};

export default function BrowserCallSimulator({ campaignId, language = "en", onComplete }: Props) {
  const [phase, setPhase]         = useState<Phase>("idle");
  const [session, setSession]     = useState<SessionOut | null>(null);
  const [result, setResult]       = useState<RespondResult | null>(null);
  const [error, setError]         = useState<string | null>(null);
  const [transcript, setTranscript] = useState("");
  const [elapsed, setElapsed]     = useState(0);

  const audioRef    = useRef<HTMLAudioElement | null>(null);
  const mrRef       = useRef<MediaRecorder | null>(null);
  const chunksRef   = useRef<Blob[]>([]);
  const timerRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const recogRef    = useRef<any>(null);
  const speechTextRef = useRef<string>("");

  const startTimer = () => {
    setElapsed(0);
    timerRef.current = setInterval(() => setElapsed((t) => t + 100), 100);
  };
  const stopTimer = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  };
  useEffect(() => () => stopTimer(), []);

  // ── Play audio blob in browser ─────────────────────────────────────────────
  const playBlob = useCallback((blob: Blob): Promise<void> => {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended  = () => { URL.revokeObjectURL(url); resolve(); };
      audio.onerror  = () => { URL.revokeObjectURL(url); reject(new Error("Audio playback failed")); };
      audio.play().catch(reject);
    });
  }, []);

  // ── Speak text via browser TTS (fallback) ──────────────────────────────────
  const speak = useCallback((text: string, lang = "en"): Promise<void> => {
    return new Promise((resolve) => {
      window.speechSynthesis.cancel();
      const utt = new SpeechSynthesisUtterance(text);
      utt.lang = lang;
      utt.rate = 0.95;
      utt.onend = () => resolve();
      setTimeout(resolve, 8000); // Fallback timeout
      window.speechSynthesis.speak(utt);
    });
  }, []);

  // ── Submit DTMF keypad key ────────────────────────────────────────────────
  const submitDtmf = useCallback(async (digit: string, activeSessionId?: string) => {
    const sId = activeSessionId || session?.id;
    if (!sId) return;
    if (recogRef.current) {
      try { recogRef.current.stop(); } catch {}
    }
    if (mrRef.current && mrRef.current.state === "recording") {
      try { mrRef.current.stop(); } catch {}
    }
    setPhase("processing");
    setError(null);
    startTimer();
    try {
      const form = new FormData();
      form.append("dtmf", digit);
      if (language) form.append("language", language);
      const res = await fetch(`${API}/api/v1/sessions/browser/${sId}/respond`, {
        method: "POST", body: form,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: RespondResult = await res.json();
      stopTimer();
      setTranscript(`[Keypad: ${digit}]`);
      setResult(data);
      setPhase("responding");
      await speak(data.response_text, data.language ?? language);
      setPhase("done");
      onComplete?.(data);
    } catch (err) {
      stopTimer();
      setError(err instanceof Error ? err.message : "Failed");
      setPhase("error");
    }
  }, [session, language, speak, onComplete]);

  // ── STEP 1: Start session ──────────────────────────────────────────────────
  const startCall = useCallback(async () => {
    setPhase("starting");
    setError(null);
    setResult(null);
    setTranscript("");

    try {
      const res = await fetch(`${API}/api/v1/sessions/browser/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ campaign_id: campaignId, language }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail ?? `Session start failed (${res.status})`);
      }
      const sess: SessionOut = await res.json();
      setSession(sess);

      // ── STEP 2: Fetch TTS greeting ─────────────────────────────────────────
      setPhase("greeting");
      startTimer();
      const ttsRes = await fetch(`${API}/api/v1/sessions/browser/${sess.id}/tts`, { method: "POST" });
      if (ttsRes.ok) {
        const audioBlob = await ttsRes.blob();
        await playBlob(audioBlob);
      } else {
        // Fallback: speak the prompt_text via browser TTS
        await speak(sess.prompt_text ?? "Hello, you are invited to this campaign. Please respond after the tone.", language);
      }
      stopTimer();

      // ── STEP 3: Record user response ───────────────────────────────────────
      await beginRecording(sess.id);
    } catch (err) {
      stopTimer();
      setError(err instanceof Error ? err.message : "Call failed");
      setPhase("error");
    }
  }, [campaignId, language, playBlob, speak]);

  // ── STEP 3: Record mic ─────────────────────────────────────────────────────
  const beginRecording = useCallback(async (sessionId: string) => {
    setPhase("listening");
    chunksRef.current = [];
    speechTextRef.current = "";
    startTimer();

    // Start Web Speech Recognition if supported by the browser
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRec) {
      try {
        const recog = new SpeechRec();
        recog.continuous = true;
        recog.interimResults = true;
        recog.lang = language === "hi" ? "hi-IN" : language === "ta" ? "ta-IN" : language === "ml" ? "ml-IN" : "en-IN";
        recog.onresult = (event: any) => {
          let str = "";
          for (let i = 0; i < event.results.length; ++i) {
            str += event.results[i][0].transcript;
          }
          speechTextRef.current = str;
          setTranscript(str);
        };
        recog.start();
        recogRef.current = recog;
      } catch (e) {
        console.warn("Speech recognition init error", e);
      }
    }

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      // No mic or permission denied — fall back to text input
      stopTimer();
      setPhase("error");
      setError("Microphone access denied. Allow mic permissions and try again.");
      return;
    }

    // Pick best supported format
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : "audio/mp4";

    const mr = new MediaRecorder(stream, { mimeType });
    mrRef.current = mr;

    mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    mr.onstop = async () => {
      if (recogRef.current) {
        try { recogRef.current.stop(); } catch {}
      }
      stream.getTracks().forEach((t) => t.stop());
      stopTimer();
      await submitResponse(sessionId, speechTextRef.current);
    };

    mr.start(250); // Collect data every 250ms
    // Auto-stop after 8s
    setTimeout(() => { if (mr.state === "recording") mr.stop(); }, 8000);
  }, [language]);

  const stopRecording = useCallback(() => {
    if (mrRef.current?.state === "recording") mrRef.current.stop();
  }, []);

  // ── STEP 4: Submit audio → backend STT + intent ────────────────────────────
  const submitResponse = useCallback(async (sessionId: string, spokenText = "") => {
    setPhase("processing");
    startTimer();

    try {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const form = new FormData();
      form.append("audio", blob, "response.webm");
      if (spokenText) form.append("text", spokenText);
      if (language) form.append("language", language);

      const res = await fetch(`${API}/api/v1/sessions/browser/${sessionId}/respond`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail ?? `Processing failed (${res.status})`);
      }

      const data: RespondResult = await res.json();
      stopTimer();

      setTranscript(data.transcript ?? spokenText ?? "");
      setResult(data);

      // ── STEP 5: Speak response ─────────────────────────────────────────────
      setPhase("responding");
      await speak(data.response_text ?? "Thank you for your response.", data.language ?? language);

      setPhase("done");
      onComplete?.(data);
    } catch (err) {
      stopTimer();
      setError(err instanceof Error ? err.message : "Processing failed");
      setPhase("error");
    }
  }, [language, speak, onComplete]);

  // ── Text-only fallback (type your response) ────────────────────────────────
  const [textInput, setTextInput] = useState("");
  const submitText = useCallback(async () => {
    if (!session || !textInput.trim()) return;
    setPhase("processing");
    setError(null);
    startTimer();
    try {
      const form = new FormData();
      form.append("text", textInput.trim());
      form.append("language", language);
      const res = await fetch(`${API}/api/v1/sessions/browser/${session.id}/respond`, {
        method: "POST", body: form,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: RespondResult = await res.json();
      stopTimer();
      setTranscript(data.transcript ?? textInput);
      setResult(data);
      setPhase("responding");
      await speak(data.response_text, data.language ?? language);
      setPhase("done");
      onComplete?.(data);
    } catch (err) {
      stopTimer();
      setError(err instanceof Error ? err.message : "Failed");
      setPhase("error");
    }
  }, [session, textInput, language, speak, onComplete]);

  // ── UI helpers ─────────────────────────────────────────────────────────────
  const LABELS: Record<Phase, string> = {
    idle:       "Ready to simulate a live call",
    starting:   "Setting up call session…",
    greeting:   "🔊 AI is speaking greeting…",
    listening:  "🎙 Recording your response… (auto-stops in 8s)",
    processing: "🧠 Transcribing + classifying intent…",
    responding: "🔊 AI is responding…",
    done:       "✅ Call complete",
    error:      "❌ Call failed",
  };

  const isActive = !["idle", "done", "error"].includes(phase);

  return (
    <div style={{ background: "#FFFDF8", border: "1.5px solid rgba(23,38,58,.1)", borderRadius: 16, padding: "20px 22px", fontFamily: "Manrope, sans-serif", maxWidth: 500 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
        <div style={{ width: 40, height: 40, borderRadius: "50%", background: phase === "done" ? "#16a34a" : phase === "error" ? "#dc2626" : isActive ? "#EA1D2C" : "#17263A", display: "grid", placeItems: "center", flex: "none", transition: "background .3s" }}>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.15 12 19.79 19.79 0 0 1 1.07 3.38 2 2 0 0 1 3 1h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L7.09 8.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21 16z"/>
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ margin: 0, fontWeight: 800, fontSize: 14, color: "#17263A" }}>Browser Call Simulator</p>
          <p style={{ margin: 0, fontSize: 11, color: "#8A9BB0" }}>Session: {session?.id?.slice(0, 8) ?? "—"} · ElevenLabs voice</p>
        </div>
        {isActive && (
          <span style={{ fontVariantNumeric: "tabular-nums", fontSize: 12, color: "#8A9BB0", flex: "none" }}>
            {(elapsed / 1000).toFixed(1)}s
          </span>
        )}
      </div>

      {/* Status */}
      <div style={{ background: "rgba(23,38,58,.04)", borderRadius: 10, padding: "10px 14px", marginBottom: 12 }}>
        <p style={{ margin: 0, fontWeight: 700, fontSize: 13, color: "#17263A" }}>{LABELS[phase]}</p>
        {transcript && phase !== "idle" && (
          <p style={{ margin: "4px 0 0", fontSize: 12, color: "#5A6E84", fontStyle: "italic" }}>"{transcript}"</p>
        )}
      </div>

      {/* Result */}
      {result && (
        <div style={{ border: `2px solid ${INTENT_COLOR[result.intent] ?? "#64748b"}22`, background: `${INTENT_COLOR[result.intent] ?? "#64748b"}08`, borderRadius: 10, padding: "12px 14px", marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <span style={{ fontWeight: 800, fontSize: 13, color: INTENT_COLOR[result.intent] ?? "#64748b", textTransform: "uppercase", letterSpacing: ".06em" }}>
              {result.intent}
            </span>
            <span style={{ fontSize: 10, color: "#8A9BB0", fontWeight: 600 }}>
              {result.confidence != null ? `${(result.confidence * 100).toFixed(0)}% · ` : ""}{result.decision_method}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: "#17263A" }}>{result.response_text}</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 8, padding: "9px 12px", marginBottom: 12, fontSize: 12, color: "#dc2626", fontWeight: 600 }}>
          {error}
        </div>
      )}

      {/* Quick DTMF Keypad shortcuts */}
      {phase === "listening" && (
        <div style={{ marginBottom: 10, background: "rgba(23,38,58,.03)", padding: "10px 12px", borderRadius: 10, border: "1px solid rgba(23,38,58,.06)" }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#8A9BB0", marginBottom: 6, textTransform: "uppercase", letterSpacing: ".06em" }}>
            Speak into mic OR tap response:
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6 }}>
            <button
              onClick={() => submitDtmf("1")}
              style={{ padding: "6px 4px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 6, color: "#16a34a", fontWeight: 700, fontSize: 11, cursor: "pointer" }}
            >
              [ 1 ] Accept
            </button>
            <button
              onClick={() => submitDtmf("2")}
              style={{ padding: "6px 4px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, color: "#dc2626", fontWeight: 700, fontSize: 11, cursor: "pointer" }}
            >
              [ 2 ] Decline
            </button>
            <button
              onClick={() => submitDtmf("3")}
              style={{ padding: "6px 4px", background: "#fffbeb", border: "1px solid #fef3c7", borderRadius: 6, color: "#d97706", fontWeight: 700, fontSize: 11, cursor: "pointer" }}
            >
              [ 3 ] Later
            </button>
            <button
              onClick={() => submitDtmf("9")}
              style={{ padding: "6px 4px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, color: "#64748b", fontWeight: 700, fontSize: 11, cursor: "pointer" }}
            >
              [ 9 ] Opt Out
            </button>
          </div>
        </div>
      )}

      {/* Text input when listening or idle after error */}
      {phase === "listening" && (
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submitText()}
            placeholder="Or type your response instead…"
            style={{ flex: 1, border: "1.5px solid rgba(23,38,58,.12)", borderRadius: 8, padding: "8px 12px", fontFamily: "Manrope, sans-serif", fontSize: 13 }}
          />
          <button onClick={submitText} style={{ padding: "8px 14px", background: "#17263A", color: "#fff", border: "none", borderRadius: 8, fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 12, cursor: "pointer" }}>Send</button>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {(phase === "idle" || phase === "done" || phase === "error") && (
          <button
            onClick={startCall}
            style={{ background: "#EA1D2C", color: "#fff", border: "none", borderRadius: 8, padding: "9px 18px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}
          >
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/></svg>
            {phase === "idle" ? "Start Call" : "Try Again"}
          </button>
        )}

        {phase === "listening" && (
          <button
            onClick={stopRecording}
            style={{ background: "#17263A", color: "#fff", border: "none", borderRadius: 8, padding: "9px 18px", fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}
          >
            <span style={{ width: 10, height: 10, background: "#EA1D2C", borderRadius: 2, display: "inline-block" }} />
            Stop & Submit
          </button>
        )}

        {isActive && (
          <button
            onClick={() => {
              audioRef.current?.pause();
              mrRef.current?.state === "recording" && mrRef.current.stop();
              window.speechSynthesis.cancel();
              stopTimer();
              setPhase("idle");
              setSession(null);
            }}
            style={{ background: "transparent", color: "#8A9BB0", border: "1.5px solid rgba(23,38,58,.1)", borderRadius: 8, padding: "9px 14px", fontFamily: "Manrope, sans-serif", fontWeight: 600, fontSize: 13, cursor: "pointer" }}
          >
            End Call
          </button>
        )}
      </div>
    </div>
  );
}
