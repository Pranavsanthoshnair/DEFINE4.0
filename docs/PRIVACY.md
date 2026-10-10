# Privacy Notice

**Veylo · DEFINE 4.0 · PR 002**

## Data Inventory

| Data Category | What we store | Where | Retention | Deletion |
|---|---|---|---|---|
| Contact phone numbers | AES-256-GCM encrypted (`phone_enc`), HMAC hash for lookup | Supabase (hosted, ap-southeast-1) | Until erased | Crypto-shredded (H3) |
| Contact names | AES-256-GCM encrypted (`name_enc`) | Supabase | Until erased | Crypto-shredded |
| Campaign scripts | Plaintext (no personal data) | Supabase | Until campaign deleted | Standard delete |
| Call recordings | Encrypted with per-contact DEK derived from contact's key | Supabase Storage | 30 days (configurable) | Key destruction renders unreadable |
| Speech-to-text output | Intent label + confidence only, no transcript stored | In-memory during call | Not persisted | N/A |
| TTS audio | Pre-rendered from script text (no personal data) | Backend memory cache, 24h TTL | 24 hours | Automatic expiry |
| Audit log | Event type, timestamp, contact UUID only | Supabase | 90 days | Hash chain preserved |

## Processing Locations

| Operation | Processor | Location | Data sent |
|---|---|---|---|
| Telephony (calls) | Exotel | India (ap-south) | Phone number, call audio |
| TTS voice generation | ElevenLabs API | US/EU | Script text only (no personal data) |
| Speech-to-text | Self-hosted Whisper | Render (US) | Call recording audio |
| Intent classification | Self-hosted model | Render (US) | STT text |
| Database | Supabase | ap-southeast-1 | All stored data |
| Backend API | Render | US | All API calls |
| Frontend | Vercel / local | — | No personal data stored |

> Note: The telephony provider (Exotel) necessarily carries call audio. All other personal data processing is on our own infrastructure or uses text-only inputs.

## Consent and DND

- Every contact requires explicit consent before being called (`consent = true`).
- Contacts on the Indian DND registry are checked and excluded before dispatch.
- Key 9 during any call immediately opts out the contact and adds their number to the suppression filter.
- Opted-out contacts are never called by any campaign, even after their record is deleted.

## Suppression Design (H2)

We use a **keyed scalable Bloom filter** to remember opted-out numbers after their contact record is deleted.

- The filter stores `HMAC-SHA256(BLOOM_HMAC_KEY, E.164(phone))` — never the phone number itself.
- **Zero false negatives**: an opted-out number is never called.
- False positives (~0.1%): a legitimate number is occasionally skipped. This is the safe failure direction.
- The filter has no delete operation. Opt-outs are permanent in v1.

**Honest limitation**: The filter hides the list, not membership against someone who holds the HMAC key. The key must be protected accordingly.

## Crypto-Shredding (H3)

Each contact's data is encrypted with their own **data encryption key (DEK)**. DEKs are wrapped with a master key (KEK) and stored in a separate key store.

To erase a contact:
1. DEK is destroyed in the key store.
2. Contact row and campaign_contacts rows are deleted.
3. All ciphertext (including copies in database backups) becomes permanently unreadable.

**Honest limitation**: Erasure is complete once the key-store backup retention window (7 days) has passed. We state this plainly. We do not claim instant erasure from all copies.

## Audit Chain (H4)

Every sensitive operation is recorded in `audit_log` with a SHA-256 hash chain. Editing any historical row breaks every hash after it. The chain head is shown on the admin page.

**Honest limitation**: Tamper-evident, not tamper-proof. Someone with database write access could rebuild the chain unless the head is anchored externally.

## Small-Cell Suppression (H7)

Dashboard breakdowns suppress any cell with fewer than 5 contacts, shown as `< 5`. This prevents identification of individuals from aggregate statistics.

## Known Limitations

- DEK encryption not yet enforced for all columns in v1 demo (framework in place).
- Suppression filter is in-memory on Render; persistence requires a mounted volume.
- Legal compliance (TRAI, PDPB) depends on deployment configuration; not claimed here.
- Call audio passes through Exotel's infrastructure.

## Contact

For data requests or questions: see `admin@example.com` (update before production).
