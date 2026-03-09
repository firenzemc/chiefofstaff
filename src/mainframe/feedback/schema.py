"""
Feedback schema definitions.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional


class FeedbackType(str, Enum):
    """Types of feedback."""
    INTENT_CORRECTION = "intent_correction"
    ENTITY_CORRECTION = "entity_correction"
    ROUTE_CHANGE = "route_change"
    APPROVAL = "approval"


class IntentFeedback(BaseModel):
    """Feedback on extracted intent."""
    feedback_id: str
    meeting_id: str
    original_intent_id: str
    feedback_type: FeedbackType
    
    # Original vs Corrected
    original_type: Optional[str] = None
    corrected_type: Optional[str] = None
    
    original_content: Optional[str] = None
    corrected_content: Optional[str] = None
    
    original_target: Optional[str] = None
    corrected_target: Optional[str] = None
    
    # Context
    feedback_text: Optional[str] = None
    reviewer_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Resolution
    resolved: bool = False
    resolved_at: Optional[datetime] = None
