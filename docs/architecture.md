# 会议 Mainframe - 技术架构设计

## 1. 竞品调研

| 项目 | Stars | 说明 | 可借鉴点 |
|------|-------|------|---------|
| Zackriya-Solutions/meetily | 10,247 | 本地优先AI会议助手，Whisper转录+Ollama总结 | 本地处理模式 |
| langgenius/dify | 131,687 | 生产级Agent工作流开发平台 | 工作流编排 |
| deepset-ai/haystack | 24,435 | 开源AI编排框架，构建RAG | 组件化设计 |
| neuml/txtai | 12,264 | 语义搜索+LLM编排 | 轻量级方案 |

**结论**：没有直接竞品。现有方案都是"会议纪要"，不是"消息总线"。

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         会议 Mainframe                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│  │   输入层     │    │   处理层     │    │   理解层     │              │
│  │  Input      │    │  Process    │    │  Understand │              │
│  ├─────────────┤    ├─────────────┤    ├─────────────┤              │
│  │ • 飞书API   │    │ • Whisper   │    │ • LLM调用   │              │
│  │ • 文件上传  │───▶│ • 音频切片   │───▶│ • 意图识别  │              │
│  │ • Webhook  │    │ • 说话人分离 │    │ • 结构化   │              │
│  └─────────────┘    └─────────────┘    └──────┬──────┘              │
│                                                │                     │
│  ┌─────────────┐    ┌─────────────┐           │                     │
│  │   审计层     │◀───│   路由层     │◀──────────┤                     │
│  │  Audit      │    │   Router    │           │                     │
│  ├─────────────┤    ├─────────────┤    ┌──────▼──────┐             │
│  │ • 执行记录  │    │ • 规则引擎  │    │ • 业务连接  │             │
│  │ • 人工确认  │◀───│ • Agent映射 │───▶│ • Connector │             │
│  │ • 追溯查询  │    │ • 触发动作  │    │ • Webhook  │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

开源范围：输入层 + 处理层 + 理解层 + 路由层协议
闭源范围：Connector（商业差异化）
```

---

## 3. 核心模块接口定义

### 3.1 输入层 (Input Layer)

```python
# 输入适配器接口
class MeetingSource(Protocol):
    async def fetch_audio() -> bytes: ...
    async def get_metadata() -> MeetingMetadata: ...

# 飞书实现
class FeishuMeetingSource(MeetingSource):
    def __init__(self, app_id: str, app_secret: str):
        self.client = FeishuClient(app_id, app_secret)
    
    async def fetch_audio(self, meeting_id: str) -> bytes:
        # 获取飞书会议录音
        recording_url = await self.client.get_recording(meeting_id)
        return await download_audio(recording_url)
    
    async def get_metadata(self, meeting_id: str) -> MeetingMetadata:
        return await self.client.get_meeting_info(meeting_id)

# 文件上传实现
class FileUploadSource(MeetingSource):
    async def fetch_audio(self, file_path: str) -> bytes:
        return Path(file_path).read_bytes()
```

### 3.2 处理层 (Processing Layer)

```python
# 转录服务
class TranscriptionService:
    def __init__(self, model: str = "base"):
        self.model = model  # whisper-small/base/large
    
    async def transcribe(self, audio: bytes) -> Transcript:
        # 调用 Whisper 转录
        result = await whisper_transcribe(audio, self.model)
        return Transcript(
            segments=result.segments,
            language=result.language,
            duration=result.duration
        )

# 说话人分离 (Diarization)
class SpeakerDiarization:
    async def identify(self, audio: bytes, transcript: Transcript) -> List[SpeakerSegment]:
        # 使用 pyannote.audio 或类似库
        return await pyannote.diarize(audio)
```

### 3.3 理解层 (Understanding Layer) - 核心

```python
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class IntentType(str, Enum):
    DECISION = "decision"           # 决策
    ACTION_ITEM = "action_item"    # 待办
    QUERY = "query"                 # 查询需求
    RISK = "risk"                   # 风险
    PROMISE = "promise"             # 承诺
    INFO = "info"                   # 信息分享

class ExtractedIntent(BaseModel):
    type: IntentType
    content: str
    confidence: float  # 0.0-1.0
    speaker: str
    timestamp: float   # 会议中的时间戳
    entities: List[dict]  # 提取的实体 (人名、日期、数量等)

class MeetingUnderstanding(BaseModel):
    intents: List[ExtractedIntent]
    summary: str
    key_decisions: List[str]
    action_items: List[dict]
    risks: List[str]

# LLM 意图提取服务
class IntentExtractionService:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    async def extract(self, transcript: Transcript) -> MeetingUnderstanding:
        # 构建 prompt
        prompt = self._build_prompt(transcript)
        
        # 调用 LLM
        response = await self.llm.chat([
            {"role": "system", "content": INTENT_EXTRACTION_PROMPT},
            {"role": "user", "content": prompt}
        ])
        
        # 解析 JSON 响应
        return MeetingUnderstanding.model_validate_json(response.content)

INTENT_EXTRACTION_PROMPT = """
你是一个会议分析专家。请分析以下会议记录，提取结构化信息。

输出 JSON 格式：
{
  "intents": [
    {
      "type": "decision|action_item|query|risk|promise|info",
      "content": "具体内容",
      "confidence": 0.0-1.0,
      "speaker": "说话人",
      "timestamp": 时间戳(秒),
      "entities": [{"type": "person|date|number|...", "value": "..."}]
    }
  ],
  "summary": "会议总结(100字)",
  "key_decisions": ["决策1", "决策2"],
  "action_items": [{"who": "人", "what": "任务", "when": "日期"}],
  "risks": ["风险1", "风险2"]
}

会议记录：
{transcript}
"""
```

### 3.4 路由层 (Router Layer)

```python
from dataclasses import dataclass
from typing import Callable, Awaitable

@dataclass
class RouteRule:
    intent_type: IntentType
    condition: Callable[[ExtractedIntent], bool]
    target: str  # agent identifier or webhook URL

class Router:
    def __init__(self):
        self.rules: List[RouteRule] = []
        self.default_route = "human-review"
    
    def add_rule(self, rule: RouteRule):
        self.rules.append(rule)
    
    async def route(self, intent: ExtractedIntent) -> str:
        for rule in self.rules:
            if rule.intent_type == intent.type and rule.condition(intent):
                return rule.target
        return self.default_route

# 预定义规则
DEFAULT_ROUTING_RULES = [
    RouteRule(
        intent_type=IntentType.DECISION,
        condition=lambda i: i.confidence > 0.8,
        target="knowledge-base"
    ),
    RouteRule(
        intent_type=IntentType.ACTION_ITEM,
        condition=lambda i: True,
        target="task-manager"
    ),
    RouteRule(
        intent_type=IntentType.QUERY,
        condition=lambda i: True,
        target="data-connector"
    ),
]
```

### 3.5 集成层 (Connector Layer) - 闭源

```python
# Connector 基类 (抽象)
class Connector(ABC):
    @abstractmethod
    async def execute(self, action: dict) -> ExecutionResult: ...

# 具体 Connector 实现
class WangdianTongConnector(Connector):
    async def execute(self, action: dict) -> ExecutionResult:
        # 调用旺店通 API
        pass

class FeishuConnector(Connector):
    async def execute(self, action: dict) -> ExecutionResult:
        # 发送飞书消息 / 创建任务
        pass
```

### 3.6 审计层 (Audit Layer)

```python
@dataclass
class ExecutionRecord:
    intent_id: str
    route: str
    connector: str
    status: str  # pending/approved/executed/failed
    created_at: datetime
    executed_at: Optional[datetime]
    result: Optional[dict]

class AuditLog:
    def __init__(self, db: Database):
        self.db = db
    
    async def record(self, record: ExecutionRecord):
        await self.db.insert("audit_log", record.model_dump())
    
    async def query(self, meeting_id: str) -> List[ExecutionRecord]:
        return await self.db.query("audit_log", meeting_id=meeting_id)
```

---

## 4. MVP 实现路径

### 4.1 核心文件清单

| 文件 | 功能 | 预估行数 |
|------|------|---------|
| `main.py` | FastAPI 入口，API 路由 | 50 |
| `models.py` | Pydantic 模型定义 | 80 |
| `transcription.py` | Whisper 转录封装 | 60 |
| `intent_extraction.py` | LLM 意图提取 | 100 |
| `router.py` | 路由规则引擎 | 80 |
| `connectors/base.py` | Connector 抽象接口 | 30 |
| `connectors/mock.py` | Mock Connector (MVP用) | 40 |
| `audit.py` | 审计日志 | 50 |
| `tests/test_pipeline.py` | 端到端测试 | 100 |
| **总计** | | **~590行** |

### 4.2 MVP 时间估算

| 阶段 | 任务 | 天数 |
|------|------|------|
| 1 | 项目初始化 + Whisper 集成 | 0.5 |
| 2 | LLM 意图提取 (prompt engineering) | 1 |
| 3 | 路由规则引擎 | 0.5 |
| 4 | Mock Connector + API 封装 | 1 |
| 5 | 审计日志 + 简单 Web UI | 1 |
| 6 | 测试 + 调优 | 1 |
| **总计** | | **5天** |

### 4.3 技术栈

- **后端**: FastAPI (Python 3.11+)
- **转录**: faster-whisper
- **LLM**: OpenAI API / Anthropic (可插拔)
- **数据库**: SQLite (MVP) / PostgreSQL (生产)
- **前端**: 简单 HTML + JS (MVP)

---

## 5. 开源策略

### 开源范围 (Core)
```
meeting-mainframe-core/
├── src/
│   ├── transcription/     # Whisper 封装
│   ├── understanding/     # LLM 意图提取
│   ├── router/            # 路由协议
│   └── audit/             # 审计接口
├── tests/
├── README.md
└── LICENSE
```

### 闭源范围 (Commercial)
- `connectors/wangdiantong.py` - 旺店通集成
- `connectors/erp.py` - ERP 集成
- `ui/` - 完整 Web 界面

---

## 6. 下一步

1. ✅ 架构设计完成
2. ⏳ 代码实现 (5天)
3. ⏳ 开源 Core 模块
4. ⏳ 商业 Connector 开发
