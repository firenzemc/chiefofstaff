# Feishu Connector

> IM Connector for 飞书 (Feishu/Lark)

## What this does
Sends messages and creates tasks in 飞书.

## Why it exists
飞书 is the dominant collaboration tool in China. Every meeting decision should be able to trigger a 飞书 message or task.

## Key concepts

- **Message**: Send to group or user
- **Task**: Create 飞书 task with assignee and due date
- **Approval**: Human-in-the-loop confirmation

## Interfaces

```python
from pydantic import BaseModel

class FeishuMessage(BaseModel):
    receive_id: str
    msg_type: str = "text"
    content: str

class FeishuTask(BaseModel):
    title: str
    assignee: str
    due_date: Optional[str]
    description: Optional[str]

class FeishuConnector:
    async def send_message(self, msg: FeishuMessage) -> str: ...
    async def create_task(self, task: FeishuTask) -> str: ...
```
