# Router Module

## What this does
Routes extracted intents to the correct target systems.

## Why it exists
An intent without routing is useless. The router maps intents to actions—create a task, send a message, file an issue.

## Key concepts

### Targets

| Target | Examples |
|--------|----------|
| IM | 飞书, Slack, 企业微信 |
| Email | Gmail, Outlook |
| Tasks | 飞书任务, Jira, Linear |
| Code | GitHub Issues, PRs |
| Business | ERP, CRM |

### Rule Engine

```python
class RouteRule(BaseModel):
    intent_type: IntentType
    condition: Callable[[Intent], bool]
    target: str  # connector identifier
```

## Interfaces

```python
class Router:
    async def route(self, intent: Intent) -> RouteResult: ...
    async def execute(self, route: RouteResult) -> ExecutionResult: ...
```
