"""
Data models for the memory subsystem.

Tracks commitments across meetings and maintains entity history.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CommitmentStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Commitment(BaseModel):
    """A tracked commitment or action item that spans meetings."""

    commitment_id: str

    # Content
    content: str
    owner: str
    due_date: Optional[str] = None

    # Provenance — where it was first seen
    source_meeting_id: str
    source_intent_id: str
    source_text: str

    # Tracking
    status: CommitmentStatus = CommitmentStatus.OPEN
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_mentioned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mention_count: int = 1
    mention_meetings: List[str] = Field(default_factory=list)

    # Closure
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    closed_evidence: Optional[str] = None


class EntityFact(BaseModel):
    """A single fact about an entity, recorded from a specific meeting."""

    meeting_id: str
    fact: str
    speaker: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EntityMemory(BaseModel):
    """Accumulated knowledge about a named entity across meetings."""

    entity_type: str      # "supplier", "person", "project", etc.
    entity_value: str     # "供应商A", "Bob", "Project Phoenix"
    facts: List[EntityFact] = Field(default_factory=list)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
