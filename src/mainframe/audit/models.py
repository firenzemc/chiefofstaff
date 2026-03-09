"""
Data models for the audit subsystem.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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
    input_type: str  # "text" | "audio_file"
    input_length: int  # chars or bytes
    intent_count: int = 0
    route_count: int = 0
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
