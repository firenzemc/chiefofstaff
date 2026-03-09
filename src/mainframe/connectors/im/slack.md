# Slack Connector

> IM Connector for Slack

## What this does
Sends messages to Slack channels or users.

## Interfaces

```python
from pydantic import BaseModel

class SlackMessage(BaseModel):
    channel: str
    text: str
    blocks: Optional[List[dict]] = None

class SlackConnector:
    async def send_message(self, msg: SlackMessage) -> str: ...
    async def create_channel(self, name: str) -> str: ...
```
