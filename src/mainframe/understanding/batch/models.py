"""
Data models for batch understanding pipeline.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime, timezone


class IntentType(str, Enum):
    """Types of intents extracted from meeting transcripts."""
    DECISION = "decision"
    ACTION_ITEM = "action_item"
    OPEN_QUESTION = "open_question"
    COMMITMENT = "commitment"
    INFO = "info"


class Entity(BaseModel):
    """Extracted entity from transcript."""
    type: str
    value: str


class TranscriptSegment(BaseModel):
    """A single segment of transcript with speaker and timing."""
    speaker: str
    text: str
    start_time: float
    end_time: float


class Transcript(BaseModel):
    """Full transcript from a meeting."""
    segments: List[TranscriptSegment]
    language: str
    duration: float


class Intent(BaseModel):
    """A single intent extracted from transcript."""
    id: str
    type: IntentType
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    speaker: str
    timestamp: float
    entities: List[Entity] = Field(default_factory=list)


class ActionItem(BaseModel):
    """An action item extracted from meeting."""
    who: Optional[str] = None
    what: str
    when: Optional[str] = None


class MeetingAnalysis(BaseModel):
    """Complete analysis result for a meeting."""
    meeting_id: str
    summary: str
    intents: List[Intent]
    decisions: List[str] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    commitments: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
