# Veylo — API Reference

## Base URL

| Environment | URL |
|-------------|-----|
| Local | `http://localhost:8000` |
| Production | `https://your-backend-url.example.com` |

Interactive docs (Swagger UI): `{base_url}/docs`  
ReDoc: `{base_url}/redoc`

---

## Authentication

> 🔲 Auth integration with Supabase JWT is pending.  
> All routes are currently open for local development.

---

## Health

### `GET /health`

Returns service liveness.

**Response `200`**
```json
{ "status": "ok", "version": "0.1.0" }
```

---

## Campaigns

### `GET /api/v1/campaigns/`
List all campaigns.

**Response `200`** — array of Campaign objects (currently returns `[]`)

---

### `POST /api/v1/campaigns/`
Create a new campaign.

**Request body**
```json
{
  "name": "Q4 Outreach",
  "description": "Quarterly renewal reminder",
  "language": "en",
  "brief": "Remind customers their subscription renews in 30 days."
}
```

**Response `201`**
```json
{
  "id": "uuid",
  "name": "Q4 Outreach",
  "language": "en",
  "status": "draft",
  "created_at": "2026-10-09T06:00:00Z"
}
```

---

### `GET /api/v1/campaigns/{campaign_id}`
Get campaign by ID.

**Response `404`** if not found.

---

### `DELETE /api/v1/campaigns/{campaign_id}`
Delete a campaign.

**Response `204`** No Content.

---

## Contacts

### `GET /api/v1/contacts/`
List contacts. Returns `[]` until Supabase is wired.

---

### `POST /api/v1/contacts/import`
Import contacts from a CSV file.

**Request** — `multipart/form-data`, field `file` (`.csv` only)  
Columns: `name`, `phone`, `language` (optional)

**Response `202`**
```json
{ "message": "CSV received — import processing not yet implemented." }
```

> 🔲 CSV parsing and Supabase write are pending.

---

## Calls

### `POST /api/v1/calls/initiate`
Initiate an outbound call for a recipient.

**Response `501`** — Exotel integration not yet implemented.

---

## Analytics

### `GET /api/v1/analytics/{campaign_id}`
Return aggregate stats for a campaign.

**Response `200`**
```json
{
  "campaign_id": "uuid",
  "total_recipients": 0,
  "calls_attempted": 0,
  "calls_answered": 0,
  "calls_failed": 0,
  "completion_rate": 0.0
}
```

---

## Webhooks

### `POST /api/v1/webhooks/exotel/call-status`
Receives Exotel call-status callbacks.

**Request** — `application/x-www-form-urlencoded` (Exotel standard format)

Key fields: `CallSid`, `Status`, `From`, `To`, `Direction`

**Response `200`** — plain text `OK`

> ⚠️ Event processing is currently a stub — payload is logged but not persisted.

---

## Error Format

All errors follow FastAPI's default JSON structure:

```json
{ "detail": "Human-readable error message" }
```

HTTP status codes used: `400`, `404`, `422` (validation), `501`, `500`.
