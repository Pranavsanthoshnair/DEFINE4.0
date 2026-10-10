# Veylo Privacy & Data Architecture

## 1. Purpose and Scope
This document provides an accurate, transparent record of how Veylo processes, routes, and stores data. Veylo is engineered with privacy safeguards (such as phone hashing and encrypted rest storage), but **does not make claims of formal legal certification or compliance guarantees**. Production deployment requires legal review under applicable telecom and data protection frameworks.

The data handled includes:
- Phone numbers (HMAC-SHA256 hashed for deduplication; stored encrypted where configured)
- Contact names (stored encrypted or redacted; never passed to AI providers)
- Language preferences and segment tags
- Call recordings (stored on disk/storage; purged after retention window)
- Utterances, transcripts, and classified intents

---

## 2. Real Data Flow by Provider

| Provider | Service / Role | Data Received | Region | Does data leave our server? |
|---|---|---|---|---|
| **Supabase** | Cloud PostgreSQL database & connection pooler | Campaign metadata, contacts (phone hashes, encrypted fields), call logs, users, analytics | `ap-southeast-1` (Singapore) | Yes |
| **Exotel** | Telephony SIP trunk carrier | Decrypted destination phone number (E.164) at dial time; live duplex audio stream | India (`ap-south-1` / Mumbai) | Yes |
| **Sarvam AI** | Indic Speech AI (Translation, Bulbul TTS, Saaras STT) | Non-PII template text for translation; template text for speech synthesis; inbound caller audio bytes for transcription | India | Yes |
| **Groq** | Fast Speech-to-Text racing / fallback | Inbound caller audio bytes for Whisper transcription | US (California) | Yes |
| **ElevenLabs** | Multilingual Voice Synthesis (TTS) | Rendered script segment text only (no names or phone numbers) | US | Yes |
| **Google Gemini** | Fallback Intent Classification | Text transcript string only (no contact metadata) | US | Yes |
| **Microsoft Edge TTS** | Fallback voice prompt generation | Template script text strings only | Global Anycast | Yes |
| **Telegram** | Real-time campaign alerts & RSVP bot | Campaign alert summaries, command inputs, button callbacks. **ZERO names or phone numbers are transmitted.** | Global (Dubai / EU) | Yes |
| **Application Hosting** | Core FastAPI API & Next.js web application | Transient in-memory request processing, execution orchestration | Render / Cloud VPS (TBD) | Yes |

*Note: In local testing or simulated mode, a mock telephony provider can run without transmitting audio to Exotel.*

---

## 3. Data Inventory & Storage Locations

| Data Item | Storage Location | Form at Rest | Retention |
|---|---|---|---|
| Phone Hashes | Supabase (`contacts.phone_hash`) | HMAC-SHA256 (One-way) | Until contact deletion |
| Phone Numbers | Supabase (`contacts.phone_enc`) | AES-256-GCM | Until contact deletion |
| Contact Names | Supabase (`contacts.name_enc`) | AES-256-GCM | Until contact deletion |
| Audio Recordings | Storage / Media Directory | AES-256-GCM encrypted files | 30 days (`RECORDING_RETENTION_DAYS`) |
| Call Event Payloads | Supabase (`call_events.payload`) | Structured JSON | 90 days (`EVENT_RETENTION_DAYS`) |
| Raw Utterances / Intents | Supabase (`intents`) | Intent label & confidence (transcripts unpersisted or redacted) | Until campaign deletion |
| User Credentials | Supabase (`users`) | PBKDF2 / Argon2 password hash | Until account deletion |
| Audit Log | Supabase (`audit_log`) | Cryptographic SHA-256 chained log | Indefinite |

---

## 4. Technical Safeguards & Design Controls
- **Zero-PII to AI Providers**: Neither Sarvam AI, Groq, ElevenLabs, Gemini, nor Edge TTS receive contact names or phone numbers. Only anonymous script strings or caller voice audio are transmitted.
- **Deduplication Without Plaintext**: Phone numbers are converted to deterministic HMAC-SHA256 hashes prior to indexing, preventing plaintext database queries across campaigns.
- **Fail-Loud Database Policy**: In production (`ENVIRONMENT=production`), the application strictly disables in-memory user fallbacks and fails with HTTP 503 if persistent database connections fail.
- **Opt-Out Mechanism & Bloom Filter (H2)**: Interactive call flows support immediate opt-out (DTMF `9` or voice phrase), appending the phone hash to a keyed scalable Bloom filter to prevent future campaign inclusion with zero false negatives.
- **Telegram Privacy Verification**: The Telegram webhook and notification handler format messages strictly as abstract campaign metrics and event prompts. Recipient names and phone numbers are never injected into outbound Telegram bot payloads.

---

## 5. Known Limitations
- Veylo utilizes third-party multi-tenant cloud APIs across India, Singapore, and the US; it is **not** an air-gapped or fully self-hosted deployment.
- No automated synchronization exists with national government DND registries (e.g. TRAI); suppression operates locally per campaign database.
- The software has not undergone SOC2, ISO27001, or statutory DPDP Act third-party audits.
