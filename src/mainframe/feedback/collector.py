# Feedback Collector

Collects human corrections to feed back into intent recognition.

## What this does

- Accepts corrections from human reviewers
- Stores feedback with context
- Prepares data for model improvement

## Interfaces

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class FeedbackType(str, Enum):
    INTENT_CORRECTION = "intent_correction"
    ENTITY_CORRECTION = "entity_correction"
    ROUTE_CHANGE = "route_change"

class IntentFeedback(BaseModel):
    feedback_id: str
    original_intent_id: str
    feedback_type: FeedbackType
    
    # What was corrected
    corrected_type: Optional[IntentType]
    corrected_content: Optional[str]
    corrected_target: Optional[str]
    
    # Metadata
    feedback_text: str
    reviewer: str
    created_at: datetime

class FeedbackCollector:
    async def submit(self, feedback: IntentFeedback) -> str: ...
    async def get_pending(self) -> List[IntentFeedback]: ...
    async def export_training_data(self) -> List[dict]: ...
```
