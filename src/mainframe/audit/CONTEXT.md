# Audit Module

## What this does
Logs all routing decisions and executions for compliance and debugging.

## Why it exists
Enterprise customers need audit trails. Every decision, every action, every correction must be traceable.

## Key concepts

- **Execution Record**: What was routed, when, to where
- **Approval Queue**: Human-in-the-loop corrections
- **Compliance Export**: SOC2, ISO27001 ready exports

## Interfaces

```python
class ExecutionRecord(BaseModel):
    intent_id: str
    route: str
    connector: str
    status: str  # pending/approved/executed/failed
    created_at: datetime
    executed_at: Optional[datetime]
    result: Optional[dict]

class AuditLog:
    async def record(self, record: ExecutionRecord) -> None: ...
    async def query(self, meeting_id: str) -> List[ExecutionRecord]: ...
```
