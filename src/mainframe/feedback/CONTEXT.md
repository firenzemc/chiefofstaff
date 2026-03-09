# Feedback Module

## What this does
Collects human corrections to build a data flywheel.

## Why it exists

> The real moat is not the architecture—it's the data flywheel.

Every human correction to extracted intents improves the model's accuracy for your specific domain.

## Key concepts

### Feedback Types

| Type | Description |
|------|-------------|
| INTENT_CORRECTION | Human corrected intent type |
| ENTITY_CORRECTION | Human corrected extracted entity |
| ROUTE_CHANGE | Human changed routing target |

## Interfaces

```python
class IntentFeedback(BaseModel):
    original_intent_id: str
    corrected_type: Optional[IntentType]
    corrected_content: Optional[str]
    corrected_target: Optional[str]
    feedback_text: str
    reviewer: str
    created_at: datetime
```

## Data Flywheel

```
Human Review → Feedback Collector → Training Data → Better Models
                                                        ↓
                                                    Higher Accuracy
```
