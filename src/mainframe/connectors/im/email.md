# Email Connector

> Email connector via SMTP

## What this does
Sends emails for meeting summaries, action items, or notifications.

## Interfaces

```python
from pydantic import BaseModel
from typing import List

class EmailMessage(BaseModel):
    to: List[str]
    subject: str
    body: str
    cc: List[str] = []
    bcc: List[str] = []

class EmailConnector:
    async def send(self, msg: EmailMessage) -> str: ...
    async def send_template(self, template: str, context: dict) -> str: ...
```
