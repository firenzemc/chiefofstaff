# Feedback Schema

Defines the data format for feedback data.

## What this does

Standardizes how human corrections are represented so they can be used to improve intent recognition.

## Schema

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class FeedbackType(str, Enum):
    INTENT_CORRECTION = "intent_correction"
    ENTITY_CORRECTION = "entity_correction" 
    ROUTE_CHANGE = "route_change"
    APPROVAL = "approval"

class IntentFeedback(BaseModel):
    """Feedback on extracted intent"""
    feedback_id: str
    meeting_id: str
    original_intent_id: str
    
    feedback_type: FeedbackType
    
    # Original vs Corrected
    original_type: Optional[IntentType]
    corrected_type: Optional[IntentType]
    
    original_content: Optional[str]
    corrected_content: Optional[str]
    
    original_target: Optional[str]
    corrected_target: Optional[str]
    
    # Context
    feedback_text: Optional[str]
    reviewer_id: str
    created_at: datetime
    
    # Resolution
    resolved: bool = False
    resolved_at: Optional[datetime]
```

## Usage

This schema is used by:
- Frontend: Display correction UI
- Collector: Store corrections
- Training Pipeline: Export feedback as training data
