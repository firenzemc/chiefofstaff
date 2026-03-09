# 会议 Mainframe - Technical Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MAINFRAME                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│  │    INPUT    │    │  PROCESS    │    │ UNDERSTAND  │              │
│  ├─────────────┤    ├─────────────┤    ├─────────────┤              │
│  │ • Feishu    │    │ • Whisper   │    │ • Streaming │              │
│  │ • Zoom      │    │ • Diarize   │───▶│ • Batch     │              │
│  │ • Local Mic │    │ • Segment   │    │ • Context   │              │
│  │ • Loopback  │    │ • Chunking  │    │   Linking   │              │
│  │ • Upload    │    │             │    │             │              │
│  └─────────────┘    └─────────────┘    └──────┬──────┘              │
│                                                │                     │
│  ┌─────────────┐    ┌─────────────┐           │                     │
│  │    AUDIT    │◀───│   ROUTER    │◀──────────┤                     │
│  ├─────────────┤    ├─────────────┤    ┌──────▼──────┐             │
│  │ • Records   │    │ • Rules    │    │ • CONNECTORS │             │
│  │ • Approvals │◀───│ • Maps     │───▶│ • IM        │             │
│  │ • Trace     │    │ • Triggers │    │ • Email     │             │
│  │ • Compliance│    │             │    │ • Tasks     │             │
│  └─────────────┘    └─────────────┘    │ • GitHub   │             │
│                                       │ • ERP/CRM  │             │
│                                       └─────────────┘             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer 1: Input (输入层)

### Sources

| Source | Type | Description |
|--------|------|-------------|
| **Feishu API** | Real-time | 飞书会议 webhook |
| **Zoom Webhook** | Real-time | Zoom 会议 webhook |
| **Local Mic** | Real-time | 本地麦克风采集（线下会议） |
| **Loopback** | Real-time | 系统音频捕获（不依赖平台API） |
| **Upload** | Batch | 文件上传（mp3, m4a, wav） |

### Module: `src/mainframe/input/`

```
input/
├── api/
│   ├── feishu.py      # 飞书 API adapter
│   └── zoom.py        # Zoom webhook handler
├── local/
│   ├── mic.py         # Local microphone capture
│   └── loopback.py    # System audio loopback
└── upload/
    └── handler.py     # File upload handler
```

## Layer 2: Processing (处理层)

### Transcription

- **faster-whisper**: GPU-accelerated Whisper
- **Streaming mode**: Chunked transcription for real-time
- **Batch mode**: Full file transcription

### Diarization

- **pyannote.audio**: Speaker diarization
- Output: `(speaker_id, timestamp, text)` segments

### Module: `src/mainframe/processing/`

```
processing/
├── transcription/
│   ├── whisper.py     # Faster-Whisper wrapper
│   ├── streamer.py    # Streaming transcription
│   └── chunker.py     # Audio chunking
└── diarization/
    └── pyannote.py    # Speaker separation
```

## Layer 3: Understanding (理解层) - Core

### Streaming Intent Inference

- Small model (e.g., Qwen-0.5B)
- Low latency (< 2s)
- Real-time intent alerts

### Batch Analysis

- Large model (GPT-4 / Claude / Qwen-Max)
- High accuracy
- Human-correctable

### Context Linking

- Cross-segment entity tracking
- Topic modeling
- Decision dependency graph

### Module: `src/mainframe/understanding/`

```
understanding/
├── streaming/
│   ├── intent.py      # Real-time intent inference
│   └── alerts.py      # Alert triggers
├── batch/
│   ├── full_analysis.py   # Post-meeting analysis
│   ├── correction.py      # Human-in-the-loop correction
│   └── context.py         # Cross-segment linking
└── models/
    ├── intents.py     # Intent type definitions
    └── entities.py    # Entity extraction
```

## Layer 4: Router (路由层)

### Target Types

| Target | Examples |
|--------|----------|
| **IM** | 飞书, 企业微信, Slack |
| **Email** | Gmail, Outlook |
| **Tasks** | 飞书任务, Jira, Linear |
| **Code** | GitHub Issues, PRs |
| **Business** | ERP, CRM, WMS |

### Rule Engine

```python
class RouteRule:
    intent_type: IntentType
    condition: Callable[[Intent], bool]
    target: str  # connector identifier
```

### Module: `src/mainframe/router/`

```
router/
├── rules.py           # Rule definitions
├── matcher.py         # Intent-to-rule matching
├── targets.py         # Target registry
└── executor.py       # Action execution
```

## Layer 5: Connectors (集成层) - Commercial

### Open Source

- Basic webhook (generic)

### Commercial

| Connector | Description |
|-----------|-------------|
| **飞书** | 消息 + 任务 |
| **企业微信** | 消息 + 审批 |
| **Slack** | 消息 + 频道 |
| **GitHub** | Issues + PRs |
| **Jira** | Issues |
| **Linear** | Issues |
| **旺店通** | WMS |
| **聚水潭** | WMS |
| **Salesforce** | CRM |

### Module: `src/mainframe/connectors/`

```
connectors/
├── im/
│   ├── feishu.py
│   ├── slack.py
│   └── wecom.py
├── email/
│   └── smtp.py
├── tasks/
│   ├── jira.py
│   └── linear.py
├── github/
│   └── api.py
└── erp/
    ├── wangdiantong.py
    └── jushuitan.py
```

## Layer 6: Audit (审计层)

### Functions

- Execution logging
- Human approval workflow
- Compliance tracking
- Queryable history

### Module: `src/mainframe/audit/`

```
audit/
├── logger.py         # Execution logging
├── approval.py       # Human approval queue
├── history.py        # Query interface
└── compliance.py     # Audit trail
```

## Data Models

### Intent

```python
class IntentType(str, Enum):
    DECISION = "decision"
    ACTION_ITEM = "action_item"
    QUERY = "query"
    RISK = "risk"
    PROMISE = "promise"
    INFO = "info"

class Intent(BaseModel):
    id: str
    type: IntentType
    content: str
    confidence: float  # 0.0-1.0
    speaker: str
    timestamp: float
    entities: List[Entity]
```

### MeetingRecord

```python
class MeetingRecord(BaseModel):
    id: str
    source: str  # feishu, zoom, local, upload
    start_time: datetime
    end_time: datetime
    transcript: List[Segment]
    intents: List[Intent]
    routes: List[RouteRecord]
    status: str  # processing, completed, approved
```

## MVP Implementation

### Core Files (~590 lines)

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | 50 | FastAPI entry |
| `models.py` | 80 | Pydantic definitions |
| `transcription.py` | 60 | Whisper wrapper |
| `intent_extraction.py` | 100 | LLM extraction |
| `router.py` | 80 | Rule engine |
| `connectors/mock.py` | 40 | Mock connector |
| `audit.py` | 50 | Audit log |
| `tests/test_pipeline.py` | 100 | E2E tests |
| **Total** | **~560** | |

### Timeline: 5 days

| Day | Task |
|-----|------|
| 1 | Project setup + Whisper |
| 2 | LLM intent extraction |
| 3 | Router rules |
| 4 | Mock connector + API |
| 5 | Audit + tests |

## Open Source Strategy

### Apache 2.0 (This Repo)

- Input adapters
- Processing pipeline
- Understanding framework
- Routing protocol
- Audit interface

### Commercial

- IM connectors (飞书, Slack, etc.)
- GitHub integration
- ERP/CRM/WMS connectors
- Industry-specific models
