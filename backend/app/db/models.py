"""
SQLAlchemy 2.0 declarative models for Veylo / DEFINE 4.0.

Column names and types match CONTRACTS.md section 4 exactly.
Do NOT add columns or rename anything without a contract-change PR.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, time
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


from sqlalchemy import DateTime
class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    type_annotation_map = {
        datetime: DateTime(timezone=True)
    }


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------

class User(Base):
    """Authenticated admin / organiser accounts."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="organiser",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=_utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint("role IN ('admin','organiser')", name="ck_users_role"),
    )


# ---------------------------------------------------------------------------
# contacts
# ---------------------------------------------------------------------------

class Contact(Base):
    """Individual contact entries. Phone stored encrypted; only hash used for lookup."""

    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    phone_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    phone_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    phone_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    name_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    segment: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    dnd: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opted_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opted_out_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    campaign_contacts: Mapped[list["CampaignContact"]] = relationship(
        back_populates="contact"
    )


# ---------------------------------------------------------------------------
# templates
# ---------------------------------------------------------------------------

class Template(Base):
    """Call script template with placeholders. Presets have is_preset=True."""

    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    use_case: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(String(2), nullable=False, default="en")
    variables: Mapped[Any] = mapped_column(JSONB, nullable=True)
    script: Mapped[Any] = mapped_column(JSONB, nullable=True)
    dtmf_map: Mapped[Any] = mapped_column(JSONB, nullable=True)
    speech_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    voicemail_policy: Mapped[str] = mapped_column(
        Text, nullable=False, default="leave_message"
    )
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "use_case IN ('seminar','clinic','school','payment','custom')",
            name="ck_templates_use_case",
        ),
        CheckConstraint(
            "voicemail_policy IN ('leave_message','skip_and_retry')",
            name="ck_templates_voicemail_policy",
        ),
    )

    translations: Mapped[list["TemplateTranslation"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="template")


# ---------------------------------------------------------------------------
# template_translations
# ---------------------------------------------------------------------------

class TemplateTranslation(Base):
    """Translated segments for a template + language pair."""

    __tablename__ = "template_translations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    segments: Mapped[Any] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    source: Mapped[str] = mapped_column(Text, nullable=False, default="ai")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("template_id", "language", name="uq_template_translations_lang"),
        CheckConstraint(
            "status IN ('draft','approved')", name="ck_translations_status"
        ),
        CheckConstraint("source IN ('ai','manual')", name="ck_translations_source"),
    )

    template: Mapped["Template"] = relationship(back_populates="translations")


# ---------------------------------------------------------------------------
# campaigns
# ---------------------------------------------------------------------------

class Campaign(Base):
    """Outbound calling campaign. Owns a set of contacts and a template."""

    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    event_details: Mapped[Any] = mapped_column(JSONB, nullable=True)
    variable_overrides: Mapped[Any] = mapped_column(JSONB, nullable=True)
    languages: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=True)
    caller_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    calling_window_start: Mapped[time] = mapped_column(
        Time, nullable=False, default=time(9, 0)
    )
    calling_window_end: Mapped[time] = mapped_column(
        Time, nullable=False, default=time(21, 0)
    )
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, default="Asia/Kolkata"
    )
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_concurrent_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_policy: Mapped[Any] = mapped_column(
        JSONB,
        nullable=True,
        default=lambda: {
            "no_answer": 60,
            "busy": 30,
            "voicemail": 240,
            "failed": 15,
            "no_input": 120,
            "unclear": 1440,
            "call_later": 120,
        },
    )
    speech_confidence_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.6
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    launched_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','preparing','needs_review','ready','running','paused','completed','cancelled')",
            name="ck_campaigns_status",
        ),
    )

    template: Mapped["Template"] = relationship(back_populates="campaigns")
    campaign_contacts: Mapped[list["CampaignContact"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    audio_assets: Mapped[list["AudioAsset"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# audio_assets
# ---------------------------------------------------------------------------

class AudioAsset(Base):
    """Pre-rendered WAV files for each (campaign, language, segment_key) triple."""

    __tablename__ = "audio_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    segment_key: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    wav_path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "language", "segment_key", name="uq_audio_assets_key"
        ),
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="audio_assets")


# ---------------------------------------------------------------------------
# campaign_contacts
# ---------------------------------------------------------------------------

class CampaignContact(Base):
    """Link between a campaign and a contact, tracking per-contact call state."""

    __tablename__ = "campaign_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    segment: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_call_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "contact_id", name="uq_campaign_contacts_pair"
        ),
        CheckConstraint(
            "state IN ('pending','in_call','waiting_retry','done','exhausted','skipped')",
            name="ck_campaign_contacts_state",
        ),
        # Composite index for the scheduler query
        Index(
            "ix_campaign_contacts_dispatch",
            "campaign_id",
            "state",
            "next_attempt_at",
        ),
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="campaign_contacts")
    contact: Mapped["Contact | None"] = relationship(back_populates="campaign_contacts")
    calls: Mapped[list["Call"]] = relationship(
        back_populates="campaign_contact", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# calls
# ---------------------------------------------------------------------------

class Call(Base):
    """Individual call attempt record."""

    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    campaign_contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_call_sid: Mapped[str | None] = mapped_column(
        Text, unique=True, nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    amd_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    flow_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    flow_state: Mapped[Any] = mapped_column(
        JSONB, nullable=False, default=lambda: {}
    )
    started_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    answered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hangup_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_provider_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('initiated','ringing','in_progress','completed','failed','busy','no_answer','canceled')",
            name="ck_calls_status",
        ),
        CheckConstraint(
            "provider IN ('exotel','mock')", name="ck_calls_provider"
        ),
        CheckConstraint(
            "amd_result IN ('human','machine','unknown') OR amd_result IS NULL",
            name="ck_calls_amd_result",
        ),
        Index("ix_calls_campaign_contact_id", "campaign_contact_id"),
    )

    campaign_contact: Mapped["CampaignContact"] = relationship(
        back_populates="calls"
    )
    events: Mapped[list["CallEvent"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )
    intents: Mapped[list["Intent"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# call_events
# ---------------------------------------------------------------------------

class CallEvent(Base):
    """Raw provider webhook events, idempotent by key."""

    __tablename__ = "call_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_call_sid: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_call_events_provider_call_sid", "provider_call_sid"),
    )

    call: Mapped["Call | None"] = relationship(back_populates="events")


# ---------------------------------------------------------------------------
# intents
# ---------------------------------------------------------------------------

class Intent(Base):
    """Captured DTMF or speech intent for a specific call step."""

    __tablename__ = "intents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_key: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    stt_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "source IN ('dtmf','speech')", name="ck_intents_source"
        ),
        CheckConstraint(
            "label IN ('confirm','decline','reschedule','call_later','stop_calling','unclear')",
            name="ck_intents_label",
        ),
        Index("ix_intents_call_id", "call_id"),
    )

    call: Mapped["Call"] = relationship(back_populates="intents")


# ---------------------------------------------------------------------------
# audit_log
# ---------------------------------------------------------------------------

class AuditLog(Base):
    """Immutable audit trail for all significant actions with cryptographic hash chain (H4)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    object_type: Mapped[str] = mapped_column(Text, nullable=False)
    object_id: Mapped[str] = mapped_column(Text, nullable=False)
    ip: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[Any] = mapped_column(JSONB, nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    row_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


# ---------------------------------------------------------------------------
# dnd_numbers
# ---------------------------------------------------------------------------

class DndNumber(Base):
    """Do-Not-Disturb registry. Stored by phone_hash only — no plain numbers."""

    __tablename__ = "dnd_numbers"

    phone_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Blueprint Differentiators (H1, H2, H3)
# ---------------------------------------------------------------------------

class SlotStat(Base):
    """Thompson sampling segment-level time-slot pickup posteriors (H1)."""

    __tablename__ = "slot_stats"

    scope: Mapped[str] = mapped_column(Text, primary_key=True)              # 'campaign:<id>' or 'org'
    segment: Mapped[str] = mapped_column(Text, primary_key=True)
    slot_idx: Mapped[int] = mapped_column(Integer, primary_key=True)
    successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow, nullable=False)


class ContactSlotStat(Base):
    """Contact-level time-slot pickup observations (H1)."""

    __tablename__ = "contact_slot_stats"

    campaign_contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign_contacts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    slot_idx: Mapped[int] = mapped_column(Integer, primary_key=True)
    successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class RetryDecision(Base):
    """Explainable retry scheduler decision log with no personal data (H1, H13)."""

    __tablename__ = "retry_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    campaign_contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_mode: Mapped[str] = mapped_column(Text, nullable=False)          # 'fixed' | 'adaptive'
    slot_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sampled_theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)               # Safe explainability string
    next_attempt_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


class SuppressionLayer(Base):
    """Keyed scalable Bloom filter layer bit-arrays for privacy-preserving opt-out (H2)."""

    __tablename__ = "suppression_layers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layer_no: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    n_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    k: Mapped[int] = mapped_column(Integer, nullable=False)
    m_bits: Mapped[int] = mapped_column(Integer, nullable=False)
    bits: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


class ErasureLedger(Base):
    """Immutable log of erased contact IDs to guarantee crypto-shredding replay across backups (H3)."""

    __tablename__ = "erasure_ledger"

    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    erased_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

