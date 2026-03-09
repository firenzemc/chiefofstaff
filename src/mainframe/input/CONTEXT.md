# Input Module

## What this does
Ingests meeting data from various sources.

## Why it exists
Different meetings come from different sources—cloud APIs, local recordings, file uploads. We need a unified interface to handle all of them.

## Key concepts

| Source | Type | Description |
|--------|------|-------------|
| Feishu | API | 飞书会议 webhook |
| Zoom | API | Zoom webhook |
| Local Mic | Real-time | Local microphone capture |
| Loopback | Real-time | System audio capture |
| Upload | Batch | File upload (mp3, m4a, wav) |

## Interfaces

```python
class MeetingSource(Protocol):
    async def fetch_audio() -> bytes: ...
    async def get_metadata() -> MeetingMetadata: ...
```
