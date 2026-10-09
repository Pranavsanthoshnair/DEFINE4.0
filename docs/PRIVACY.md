# Veylo (DEFINE 4.0) Privacy and Compliance

## 1. Purpose and Scope
This document outlines how Veylo (the DEFINE 4.0 automated multilingual outbound calling platform) handles, stores, and protects personal data. The personal data we handle includes:
- Phone numbers (stored encrypted, searched via hash)
- Contact names (stored encrypted)
- Contact language preferences and segment groupings
- Call recordings (stored encrypted on disk)
- Call transcripts and intent classifications

## 2. Lawful Basis and Consent
Veylo operates strictly on a consent-based model. 
- A `consent` flag is mandatory for importing any contact. 
- The source of consent (`consent_source`) and timestamp are recorded. 
- Every call flow must provide a clearly stated opt-out mechanism (e.g., "Press 9 to stop calls").
- Contacts who opt-out are added to a local Do-Not-Disturb (DND) registry and blocked from future campaigns.
- Calling hours are restricted (default 09:00 to 21:00) per local timezone settings.
*Note: Regulations such as India's DPDP Act and TRAI commercial communication rules apply. Production use requires a formal legal review.*

## 3. Data Inventory

| Data Item | Storage Location | Encrypted at Rest? | Default Retention |
|---|---|---|---|
| Phone Numbers | Postgres (`contacts.phone_enc`) | Yes (AES-256-GCM) | Until contact deletion |
| Contact Names | Postgres (`contacts.name_enc`) | Yes (AES-256-GCM) | Until contact deletion |
| Phone Hashes | Postgres (`contacts.phone_hash`) | HMAC-SHA256 (One-way) | Until contact deletion |
| Call Recordings | Disk (`MEDIA_DIR`) | Yes (AES-256-GCM) | 30 days |
| Call Intents / Inputs | Postgres (`intents.raw_input`) | No (Plain text) | Until contact deletion |
| Call Events | Postgres (`call_events.payload`) | No (Plain text) | 90 days |
| Audit Logs | Postgres (`audit_log`) | No | Indefinite |

## 4. Processing Locations

| System / Function | Provider / Location | Does data leave our server? |
|---|---|---|
| Contact Database (Storage) | Local Postgres Database | No |
| Call Audio Storage | Local Disk (`MEDIA_DIR`) | No |
| Telephony (SIP/Trunk) | Exotel (India, Mumbai AP-South-1) | Yes (Audio streams & numbers) |
| Text to Speech (TTS) | Edge TTS (Microsoft) / Local | Yes (Template text only, no PII) |
| Speech to Text (STT) | Local Whisper (Faster-Whisper) | No |
| Intent Classification | Local LLM / Rule-based | No |
| Translation | Local LLM / API Fallback | Yes (If fallback used) |

*Note: The server hosting this instance must be verified for its physical location by the administrator. Currently assumed to be self-hosted or VPS in India.*

## 5. Third-Party Processors
- **Exotel**: Receives the decrypted E.164 phone numbers at the exact time of calling to establish the SIP bridge. Handles the live audio stream.
- **Microsoft Edge TTS**: Receives anonymized template text strings to generate audio prompts. Does not receive contact names or phone numbers.
- **Gemini / Groq (Optional Fallbacks)**: If the local AI microservice fails or is bypassed, these services may receive non-PII template text for translation or intent classification.

## 6. Security Measures
- **Encryption at Rest**: Phone numbers, names, and recorded audio files are encrypted using AES-256-GCM.
- **Encryption in Transit**: All internal API and Webhook traffic should run over HTTPS/TLS in production.
- **Key Handling**: Cryptographic keys are injected via environment variables (`DATA_ENC_KEY`, `PHONE_HMAC_KEY`) and never committed to source control.
- **Access Control**: Role-based access (Admin vs Organiser) using JWT HS256 tokens.
- **Audit Logging**: All significant actions (imports, retries, deletions, recording playbacks) write immutable records to the `audit_log` table.
- **Log Redaction**: Strict structural logging rules prevent plain phone numbers, names, or transcripts from being printed to `stdout` or log files.
- **Webhook Security**: Inbound provider events are verified using an HMAC/Secret token (`WEBHOOK_SECRET`).

## 7. Retention and Deletion
- **Call Recordings**: Automatically purged after `RECORDING_RETENTION_DAYS` (default 30) via a scheduled daily Celery task (`maintenance.purge_expired_recordings`).
- **Call Events**: Raw webhook payloads are purged after `EVENT_RETENTION_DAYS` (default 90).
- **Erasure Endpoint**: An admin-only `DELETE /api/contacts/{id}` endpoint allows full data subject erasure (deletes recordings, clears text inputs, and removes the contact row while preserving anonymous statistical counters).

## 8. Data Subject Rights and Contact
Data subjects have the right to request access to or deletion of their personal data. 
- Organisers can facilitate deletions via the admin dashboard.
- For compliance inquiries regarding a specific deployment of Veylo, please contact the deploying organization's Data Protection Officer.

## 9. Known Limitations
- The current implementation uses local Edge TTS which may transmit text to Microsoft endpoints (without a formal DPA).
- There is no automated integration with the national TRAI DND registry (only a local blocklist is maintained).
- Deployments on a single VPS lack physical hardware isolation guarantees.
- The software has not undergone formal SOC2 or ISO27001 certification.
