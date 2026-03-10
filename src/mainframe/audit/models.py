"""
Data models for the audit subsystem.

Covers both pipeline-level runs (PipelineRun) and per-intent execution
records (ExecutionRecord) with provenance, risk assessment, and rollback.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pipeline run (Phase 1 — unchanged)
# ---------------------------------------------------------------------------

class PipelineRunStatus(str, Enum):
    STARTED = "started"
    EXTRACTING = "extracting"
    ROUTING = "routing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineRun(BaseModel):
    """Record of a single pipeline execution."""

    run_id: str
    meeting_id: str
    status: PipelineRunStatus
    input_type: str
    input_length: int
    intent_count: int = 0
    route_count: int = 0
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


# ---------------------------------------------------------------------------
# Risk level (Phase 2A)
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    """Operation risk — determines whether human approval is required."""

    LOW = "low"            # Auto-execute: write to doc, log
    MEDIUM = "medium"      # Execute then notify: create task, send IM
    HIGH = "high"          # Require approval before execution: external email, modify amounts
    CRITICAL = "critical"  # Require approval + second confirmation: money, contracts


# ---------------------------------------------------------------------------
# Execution lifecycle (Phase 2A)
# ---------------------------------------------------------------------------

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ExecutionRecord(BaseModel):
    """
    Complete lifecycle record for a single routed intent.

    Tracks provenance (where it came from), risk assessment,
    execution result, and rollback information.
    """

    # Identity
    record_id: str
    meeting_id: str
    run_id: str

    # Provenance — trace back to the exact utterance
    intent_id: str
    intent_type: str
    source_speaker: str
    source_text: str
    source_timestamp: float
    confidence: float

    # Routing
    target: str
    rule_id: str
    payload: dict = Field(default_factory=dict)

    # Risk & approval
    risk_level: RiskLevel = RiskLevel.LOW
    risk_reason: str = ""
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # approval deadline for AWAITING_APPROVAL

    # Execution
    status: ExecutionStatus = ExecutionStatus.PENDING
    executed_at: Optional[datetime] = None
    execution_result: Optional[dict] = None

    # Rollback
    rollback_hint: str = ""
    rolled_back_at: Optional[datetime] = None
    rollback_result: Optional[dict] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
