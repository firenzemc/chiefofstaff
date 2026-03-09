# Understanding Module

## What this does
Extracts structured intents from transcribed meeting text.

## Why it exists
This is the core differentiator. Not just transcription—understanding what decisions were made, what tasks were assigned, what risks were raised.

## Key concepts

### Intent Types

| Type | Description |
|------|-------------|
| DECISION | A decision made in the meeting |
| ACTION_ITEM | A task assigned to someone |
| QUERY | A request for information |
| RISK | A risk or concern raised |
| PROMISE | A commitment made |
| INFO | Information shared |

### Two Modes

1. **Batch** (Phase 1): Post-meeting full analysis with large models
2. **Streaming** (Phase 2): Real-time inference with small models

## Interfaces

```python
class Intent(BaseModel):
    id: str
    type: IntentType
    content: str
    confidence: float
    speaker: str
    timestamp: float
    entities: List[Entity]
```

## Data Flywheel

Every human correction to extracted intents feeds back into improving the model for your specific domain.
