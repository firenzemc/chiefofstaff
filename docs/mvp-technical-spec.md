# MVP Technical Spec: Batch Understanding Pipeline

> **Status**: Draft v1.0  
> **Author**: dev-lead (AI Architect)  
> **Date**: 2026-03-09  
> **Scope**: Text-in → Structured intents out, end-to-end testable

---

## 1. MVP Scope Definition

### What's IN (Phase 1 — Batch Text Pipeline)

| Capability | Description |
|-----------|-------------|
| **Text transcript input** | Accept raw text ("Speaker: content" format) |
| **LLM intent extraction** | Call OpenAI-compatible API to extract structured intents |
| **Structured output** | Pydantic-validated MeetingAnalysis with decisions, action_items, open_questions, commitments |
| **Mock connector** | Dummy connector that logs routed intents (no real IM/task integration) |
| **Feedback collection** | In-memory feedback store for human corrections |
| **FastAPI endpoint** | Single POST `/analyze` endpoint |
| **Audit logging** | In-memory audit trail of pipeline runs |
| **Tests** | ≥90% coverage of pipeline code, mock-based LLM tests |

### What's OUT (deferred)

| Capability | Why deferred |
|-----------|-------------|
| Audio input / Whisper | Adds hardware dependency, text path validates the pipeline first |
| Streaming inference | Phase 2, needs different model architecture |
| Real connectors (Feishu/Slack/GitHub) | Connector protocol defined, but real integrations are post-MVP |
| Diarization (pyannote) | Only needed for audio path |
| Authentication / multi-tenancy | Post-MVP hardening |
| Persistent storage (DB) | In-memory is fine for MVP validation |

### Why this scope?

The critical risk is: **can we reliably extract structured intents from meeting text using LLM?** Everything else is plumbing. This MVP validates the core value proposition with minimal infrastructure.

---

## 2. Architecture Overview

```
POST /analyze
     │
     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  InputParser │────▶│IntentExtractor│────▶│   Router    │
│ (text→Trans) │     │  (LLM call)  │     │(rule match) │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                          ┌──────────────────────┼──────────────┐
                          ▼                      ▼              ▼
                   ┌────────────┐      ┌──────────────┐  ┌──────────┐
                   │MockConnector│      │AuditLogger   │  │Feedback  │
                   │  (log only) │      │(in-memory)   │  │Collector │
                   └────────────┘      └──────────────┘  └──────────┘
```

### Data Flow

1. **InputParser** receives raw text, parses "Speaker: content" lines into `Transcript` (reuse existing `TranscriptionService.transcribe_text`)
2. **IntentExtractor** sends transcript to LLM, parses structured JSON response into `MeetingAnalysis`
3. **Router** matches each intent against rules, produces `RouteResult` list
4. **MockConnector** "executes" each route (logs it)
5. **AuditLogger** records the full pipeline run
6. **FeedbackCollector** stores the analysis for later human review

---

## 3. Data Models (Pydantic)

### 3.1 Existing Models — KEEP as-is

These are well-defined and correct:

| Model | File | Status |
|-------|------|--------|
| `IntentType` | `understanding/batch/models.py` | ✅ Keep |
| `Entity` | `understanding/batch/models.py` | ✅ Keep |
| `TranscriptSegment` | `understanding/batch/models.py` | ✅ Keep |
| `Transcript` | `understanding/batch/models.py` | ✅ Keep |
| `Intent` | `understanding/batch/models.py` | ✅ Keep |
| `ActionItem` | `understanding/batch/models.py` | ✅ Keep |
| `MeetingAnalysis` | `understanding/batch/models.py` | ✅ Keep |
| `FeedbackType` | `feedback/schema.py` | ✅ Keep |
| `IntentFeedback` | `feedback/schema.py` | ✅ Keep |

### 3.2 Models to FIX

**Issue: CONTEXT.md vs Code mismatch on IntentType**

`understanding/CONTEXT.md` defines: `DECISION, ACTION_ITEM, QUERY, RISK, PROMISE, INFO`  
`understanding/batch/models.py` defines: `DECISION, ACTION_ITEM, OPEN_QUESTION, COMMITMENT, INFO`

**Decision**: Keep the code version. `OPEN_QUESTION` is more specific than `QUERY`, and `COMMITMENT` is more specific than `PROMISE`. Update CONTEXT.md to match code. We may add `RISK` in Phase 2 when we have multi-turn context.

### 3.3 New Models to ADD

```python
# --- router/models.py (NEW) ---

class RouteTarget(str, Enum):
    """Where an intent gets routed."""
    TASK_TRACKER = "task_tracker"    # → Create task
    IM_MESSAGE = "im_message"       # → Send notification
    DOCUMENT = "document"           # → Write to doc/wiki
    AGENT = "agent"                 # → Spawn agent (future)
    NONE = "none"                   # → No action needed

class RouteRule(BaseModel):
    """A single routing rule."""
    id: str
    intent_type: IntentType
    target: RouteTarget
    priority: int = 0               # Higher = checked first
    condition: Optional[str] = None  # Optional extra condition (future)

class RouteResult(BaseModel):
    """Result of routing a single intent."""
    intent_id: str
    intent_type: IntentType
    target: RouteTarget
    rule_id: str
    payload: dict                    # Connector-specific payload

class RoutingPlan(BaseModel):
    """Complete routing plan for a meeting analysis."""
    meeting_id: str
    routes: List[RouteResult]
    unrouted: List[str]             # Intent IDs with no matching rule
    created_at: datetime


# --- audit/models.py (NEW) ---

class PipelineRunStatus(str, Enum):
    STARTED = "started"
    EXTRACTING = "extracting"
    ROUTING = "routing"
    COMPLETED = "completed"
    FAILED = "failed"

class PipelineRun(BaseModel):
    """Record of a single pipeline execution."""
    run_id: str
    meeting_id: str
    status: PipelineRunStatus
    input_type: str                  # "text" | "audio_file"
    input_length: int                # chars or bytes
    intent_count: int = 0
    route_count: int = 0
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


# --- api/schemas.py (NEW) ---

class AnalyzeRequest(BaseModel):
    """POST /analyze request body."""
    text: str                        # Raw transcript text
    meeting_id: Optional[str] = None # Client-provided ID
    language: str = "auto"           # Language hint

class AnalyzeResponse(BaseModel):
    """POST /analyze response body."""
    meeting_id: str
    summary: str
    intents: List[Intent]
    decisions: List[str]
    action_items: List[ActionItem]
    open_questions: List[str]
    commitments: List[str]
    routes: List[RouteResult]
    run_id: str
```

---

## 4. Module Breakdown

### 4.1 File Map with Line Budgets

```
src/mainframe/
├── __init__.py                          # (existing, empty)
├── main.py                              # NEW — FastAPI app entry     ~60 lines
├── config.py                            # NEW — Settings via pydantic  ~40 lines
│
├── api/
│   ├── __init__.py                      # NEW
│   └── schemas.py                       # NEW — Request/Response      ~40 lines
│
├── understanding/
│   ├── CONTEXT.md                       # FIX — update IntentType list
│   └── batch/
│       ├── models.py                    # EXISTING — keep as-is
│       ├── transcription.py             # EXISTING — keep text path, gut audio placeholder
│       ├── intent_extractor.py          # REWRITE — real LLM integration  ~150 lines
│       └── pipeline.py                  # REFACTOR — simplify to text-only ~100 lines
│
├── router/
│   ├── __init__.py                      # EXISTING (empty)
│   ├── models.py                        # NEW — RouteTarget/Rule/Result   ~60 lines
│   ├── engine.py                        # NEW — Rule matching engine      ~80 lines
│   └── default_rules.py                 # NEW — Default rule set          ~40 lines
│
├── connectors/
│   ├── CONTEXT.md                       # EXISTING
│   ├── base.py                          # NEW — Connector protocol        ~30 lines
│   ├── mock.py                          # NEW — Mock connector for MVP    ~50 lines
│   └── im/                              # EXISTING — rename .py→.md or delete
│       ├── feishu.md                    # Was feishu.py (Markdown content)
│       ├── slack.md                     # Was slack.py
│       ├── github.md                    # Was github.py
│       └── email.md                     # Was email.py
│
├── audit/
│   ├── __init__.py                      # EXISTING (empty)
│   ├── models.py                        # NEW — PipelineRun model         ~40 lines
│   └── logger.py                        # NEW — In-memory audit logger    ~60 lines
│
├── feedback/
│   ├── schema.py                        # EXISTING — keep
│   ├── collector.py                     # EXISTING — keep, minor cleanup
│   └── __init__.py                      # EXISTING
│
├── input/                               # DEFER — not touched in MVP
│   └── ...
└── processing/                          # DEFER — not touched in MVP
    └── ...
```

**New/Modified code**: ~750 lines  
**New test code**: ~400 lines  
**Total delta**: ~1150 lines

### 4.2 Module Responsibilities

#### `main.py` — FastAPI Application Entry

```python
# Responsibilities:
# - Create FastAPI app
# - Wire up dependencies (extractor, router, audit, feedback)
# - Define POST /analyze endpoint
# - Define GET /health endpoint
# - Startup/shutdown lifecycle hooks

app = FastAPI(title="Mainframe", version="0.1.0")

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    ...
```

#### `config.py` — Application Configuration

```python
# Responsibilities:
# - Load settings from env vars / .env file
# - LLM provider config (api_key, model, base_url)
# - Whisper config (model_size, device) — for future
# - App config (host, port, debug)

class Settings(BaseSettings):
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    model_config = SettingsConfigDict(env_prefix="MAINFRAME_")
```

#### `understanding/batch/intent_extractor.py` — REWRITE

```python
# Current problems:
# - _call_llm() returns "{}" placeholder
# - No real LLM client integration
# - Mock path works but is too tightly coupled
#
# Rewrite plan:
# - Accept `openai.AsyncOpenAI` client (via openai SDK)
# - Real structured output: use response_format=json_object
# - Proper error handling: retry, fallback, timeout
# - Keep mock path for testing (llm_client=None → mock)
# - Add input validation: reject empty transcripts
# - Add output validation: parse LLM JSON with Pydantic, not manual dict access

class IntentExtractor:
    def __init__(self, client: AsyncOpenAI | None = None, model: str = "gpt-4o-mini"):
        ...

    async def extract(self, transcript: Transcript, meeting_id: str = "") -> MeetingAnalysis:
        ...

    async def _call_llm(self, transcript_text: str) -> dict:
        # Real implementation using openai SDK
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[...],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(response.choices[0].message.content)
```

#### `router/engine.py` — NEW

```python
# Responsibilities:
# - Load routing rules (from default_rules or custom)
# - Match intents to rules by type
# - Build RouteResult with connector-specific payload
# - Handle unmatched intents gracefully

class RoutingEngine:
    def __init__(self, rules: list[RouteRule] | None = None):
        ...

    def route(self, analysis: MeetingAnalysis) -> RoutingPlan:
        # For each intent, find matching rule, build RouteResult
        ...

    def _build_payload(self, intent: Intent, target: RouteTarget) -> dict:
        # Build connector-specific payload
        ...
```

#### `connectors/base.py` + `connectors/mock.py` — NEW

```python
# base.py — Protocol definition
class Connector(Protocol):
    async def execute(self, route: RouteResult) -> dict:
        """Execute a routed action. Returns result dict."""
        ...

# mock.py — MVP implementation
class MockConnector:
    """Logs actions instead of executing them. For MVP testing."""
    def __init__(self):
        self.executed: list[RouteResult] = []

    async def execute(self, route: RouteResult) -> dict:
        self.executed.append(route)
        return {"status": "mock_ok", "route_id": route.intent_id}
```

#### `audit/logger.py` — NEW

```python
# Responsibilities:
# - Record pipeline run start/end
# - Track status transitions
# - Query runs by meeting_id
# - In-memory storage (DB adapter in future)

class AuditLogger:
    def __init__(self):
        self.runs: list[PipelineRun] = []

    async def start_run(self, meeting_id: str, input_type: str, input_length: int) -> PipelineRun:
        ...

    async def complete_run(self, run_id: str, intent_count: int, route_count: int) -> None:
        ...

    async def fail_run(self, run_id: str, error: str) -> None:
        ...
```

---

## 5. Dependency Selection

### 5.1 LLM Client: `openai` SDK (Official)

**Decision**: Use the official `openai` Python SDK.

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| `openai` SDK | First-party, best docs, async support, structured output | OpenAI-only API shape | ✅ **Pick this** |
| `litellm` | 100+ providers, unified interface | Extra dep, abstraction leakage, version churn | ❌ Later |
| Raw `httpx` | No dependency | Too low-level, reinventing the wheel | ❌ No |

**Rationale**: The `openai` SDK's API shape has become the de facto standard. Most providers (DeepSeek, Together, Groq, local vLLM) expose OpenAI-compatible endpoints. By using `openai.AsyncOpenAI(base_url=...)`, we get multi-provider support without the litellm dependency. We can add litellm later if needed.

**Add to pyproject.toml**:
```toml
dependencies = [
    ...
    "openai>=1.30.0",
]
```

### 5.2 Whisper: DEFERRED

Audio transcription is out of MVP scope. The existing `faster-whisper` dependency in pyproject.toml stays, but we don't implement real audio processing yet. The text transcription path (`TranscriptionService.transcribe_text`) is sufficient.

### 5.3 Other Dependencies

| Dependency | Already in pyproject.toml | Status |
|-----------|--------------------------|--------|
| `fastapi` | ✅ | Keep — API framework |
| `uvicorn` | ✅ | Keep — ASGI server |
| `pydantic` | ✅ | Keep — Data validation |
| `faster-whisper` | ✅ | Keep but don't use in MVP |
| `python-dotenv` | ✅ | Keep — .env loading |
| `pytest` | ✅ (dev) | Keep |
| `pytest-asyncio` | ✅ (dev) | Keep |
| `openai` | ❌ NEW | **Add** |

---

## 6. Testing Strategy

### 6.1 Test Structure

```
tests/
├── conftest.py                    # Shared fixtures              ~60 lines
├── test_models.py                 # Pydantic model validation    ~50 lines
├── test_intent_extractor.py       # IntentExtractor (mock LLM)  ~100 lines
├── test_router.py                 # RoutingEngine + rules        ~80 lines
├── test_pipeline.py               # End-to-end pipeline          ~60 lines
├── test_api.py                    # FastAPI endpoint tests        ~50 lines
└── test_audit.py                  # AuditLogger tests            ~40 lines
```

### 6.2 What Gets Mocked vs. Real

| Component | Test Strategy | Why |
|-----------|--------------|-----|
| **Pydantic models** | Real — construct and validate | Zero external deps |
| **TranscriptionService.transcribe_text** | Real — pure text parsing | No I/O |
| **IntentExtractor._call_llm** | **Mock** — fake LLM JSON response | API call |
| **IntentExtractor._parse_response** | Real — parse known JSON | Pure function |
| **IntentExtractor._mock_response** | Real — test mock path | Pure function |
| **RoutingEngine.route** | Real — rule matching logic | Pure function |
| **MockConnector** | Real — it's already a mock | No I/O |
| **AuditLogger** | Real — in-memory store | No I/O |
| **FeedbackCollector** | Real — in-memory store | No I/O |
| **FastAPI endpoint** | `TestClient` + mocked extractor | Integration |

### 6.3 Key Fixtures (`conftest.py`)

```python
@pytest.fixture
def sample_transcript() -> Transcript:
    """A realistic 4-speaker meeting transcript for testing."""
    ...

@pytest.fixture
def sample_llm_response() -> dict:
    """A well-formed LLM JSON response matching our schema."""
    ...

@pytest.fixture
def sample_analysis() -> MeetingAnalysis:
    """A complete MeetingAnalysis for downstream testing."""
    ...

@pytest.fixture
def default_rules() -> list[RouteRule]:
    """Default routing rules for testing."""
    ...
```

### 6.4 Testing Principles

1. **No network calls in tests** — All LLM calls are mocked
2. **Fixtures over factories** — Use shared, realistic fixtures
3. **Test behavior, not implementation** — "given this input, expect this output"
4. **Each test file corresponds to one module** — Easy to find
5. **Async tests use `pytest-asyncio`** — Already configured in pyproject.toml

---

## 7. Known Issues to Fix

| # | Issue | Fix | Priority |
|---|-------|-----|----------|
| 1 | `understanding/CONTEXT.md` IntentType mismatch with code | Update CONTEXT.md to match code | P1 — do first |
| 2 | `connectors/im/*.py` are Markdown, not Python | Rename to `.md` | P1 — prevents SyntaxError |
| 3 | Package not installable (`ModuleNotFoundError`) | Ensure `pip install -e .` works | P0 — blocks all tests |
| 4 | Tests don't test real behavior (mostly `assert X is not None`) | Rewrite with proper assertions | P1 |
| 5 | `pipeline.py` has dead code paths (audio bytes, audio file) | Simplify to text-only for MVP | P2 |
| 6 | `_call_llm` returns `"{}"` placeholder | Implement with openai SDK | P0 — core feature |
| 7 | `FeedbackCollector.submit` accepts arbitrary dict, no validation | Add Pydantic validation | P2 |
| 8 | No `main.py` entry point | Create FastAPI app | P1 |

---

## 8. Implementation Order

### Phase 0: Infrastructure Fix (1 task)
Fix package installation, rename broken .py files, update CONTEXT.md

### Phase 1: Core Pipeline (3 tasks)
1. Rewrite `intent_extractor.py` with real openai SDK
2. Implement `router/` module (models, engine, default rules)
3. Implement `audit/` module (models, logger)

### Phase 2: API Layer (1 task)
4. Create `main.py` + `config.py` + `api/schemas.py`

### Phase 3: Testing (2 tasks)
5. Write comprehensive tests (conftest, all test files)
6. Fix existing broken tests, achieve ≥90% coverage

### Phase 4: Integration (1 task)
7. End-to-end smoke test: text in → API → structured output → mock routes

---

## 9. Task Breakdown for Team

### Task 0: Infrastructure Cleanup [dev-exec]
**Input**: Current broken state  
**Output**: `pip install -e ".[dev]" && pytest` runs (even if tests fail)  
**Acceptance criteria**:
- [ ] `connectors/im/*.py` renamed to `.md`
- [ ] `understanding/CONTEXT.md` IntentType updated to match code
- [ ] `openai>=1.30.0` added to pyproject.toml dependencies
- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `pytest tests/` runs without `ModuleNotFoundError`
- [ ] `processing/` module: add note that it's deferred (overlaps with understanding/batch)

### Task 1: IntentExtractor Rewrite [dev-exec]
**Input**: `understanding/batch/intent_extractor.py` (current ~160 lines)  
**Output**: Working LLM integration via openai SDK (~150 lines)  
**Acceptance criteria**:
- [ ] Constructor takes `openai.AsyncOpenAI` client + model name
- [ ] `extract()` calls LLM with structured output (response_format=json_object)
- [ ] Response parsed via Pydantic, not manual dict access
- [ ] Graceful error handling: JSON parse error → fallback to mock
- [ ] Empty transcript → raises ValueError
- [ ] `meeting_id` parameter propagated to output
- [ ] Mock path (client=None) preserved for testing
- [ ] System prompt unchanged (it's good)
- [ ] Temperature=0.1 for reproducibility

### Task 2: Router Module [dev-exec]
**Input**: Empty `router/` directory  
**Output**: `router/models.py`, `router/engine.py`, `router/default_rules.py` (~180 lines)  
**Acceptance criteria**:
- [ ] `RouteTarget`, `RouteRule`, `RouteResult`, `RoutingPlan` models defined
- [ ] `RoutingEngine` matches intents by type against rules
- [ ] Default rules: DECISION→document, ACTION_ITEM→task_tracker, OPEN_QUESTION→agent, COMMITMENT→task_tracker, INFO→none
- [ ] Unmatched intents collected in `RoutingPlan.unrouted`
- [ ] Payload builder creates target-specific dicts
- [ ] Engine is stateless — rules passed at init

### Task 3: Audit + Connector Modules [dev-exec]
**Input**: Empty `audit/`, no connector base  
**Output**: `audit/models.py`, `audit/logger.py`, `connectors/base.py`, `connectors/mock.py` (~180 lines)  
**Acceptance criteria**:
- [ ] `PipelineRun` model with status transitions
- [ ] `AuditLogger` with start/complete/fail/query methods
- [ ] `Connector` protocol defined
- [ ] `MockConnector` logs executed routes, returns mock result
- [ ] Duration tracking (started_at → completed_at → duration_ms)

### Task 4: API Layer [dev-exec]
**Input**: No main.py  
**Output**: `main.py`, `config.py`, `api/schemas.py` (~140 lines)  
**Acceptance criteria**:
- [ ] `POST /analyze` accepts `AnalyzeRequest`, returns `AnalyzeResponse`
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `Settings` loaded from env vars with `MAINFRAME_` prefix
- [ ] Dependencies wired via FastAPI's dependency injection
- [ ] Error handling: 400 for bad input, 500 for LLM failure with error detail
- [ ] `uvicorn` entrypoint: `python -m mainframe.main`

### Task 5: Test Suite [dev-exec → dev-test reviews]
**Input**: Current broken tests  
**Output**: Comprehensive test suite (~400 lines)  
**Acceptance criteria**:
- [ ] `conftest.py` with shared fixtures (sample_transcript, sample_llm_response, etc.)
- [ ] `test_models.py` — Pydantic model construction + validation edge cases
- [ ] `test_intent_extractor.py` — Mock LLM response → correct MeetingAnalysis; error handling
- [ ] `test_router.py` — Default rules match correctly; unrouted handling; custom rules
- [ ] `test_pipeline.py` — End-to-end with mocked LLM
- [ ] `test_api.py` — FastAPI TestClient integration
- [ ] `test_audit.py` — Lifecycle: start→complete, start→fail, query
- [ ] All existing tests either fixed or replaced
- [ ] `pytest tests/ -v --cov=src/mainframe` passes with ≥90% line coverage

### Task 6: Integration Smoke Test [dev-test]
**Input**: All modules implemented  
**Output**: Documented manual test procedure + automated integration test  
**Acceptance criteria**:
- [ ] Start server with mock LLM (env: `MAINFRAME_LLM_API_KEY=test`)
- [ ] `curl POST /analyze` with sample meeting transcript
- [ ] Response contains correct structured output
- [ ] Audit log contains pipeline run record
- [ ] Feedback collector contains analysis entry

---

## 10. Open Questions for Chief (需要主席决策)

### Q1: LLM Model Default — `gpt-4o-mini` vs `deepseek-chat`?

`gpt-4o-mini` has best structured output support (json_object mode). `deepseek-chat` is cheaper and works with OpenAI-compatible API. For MVP testing, either works since we mock LLM calls. But the default in config matters for first real usage.

**Recommendation**: Default to `gpt-4o-mini`, document `base_url` override for DeepSeek/other providers.

### Q2: Should we add `RISK` intent type now?

CONTEXT.md mentions it, code doesn't have it. Adding it is trivial (one enum value + one routing rule). But it means the LLM prompt and mock path both need updating.

**Recommendation**: Defer to Phase 2. Current 5 types cover MVP use cases. Adding it later is backwards-compatible.

### Q3: `processing/` module — delete or keep as stub?

It duplicates `understanding/batch/transcription.py` in concept. Keeping it creates confusion about where transcription lives.

**Recommendation**: Keep the directory with a `DEFERRED.md` note. Don't delete — it's in the architecture doc and git history. Consolidate in Phase 2 when we add real audio.

---

## Appendix A: Sequence Diagram

```
Client                FastAPI              Pipeline            IntentExtractor       Router
  │                     │                    │                      │                  │
  │ POST /analyze       │                    │                      │                  │
  │────────────────────▶│                    │                      │                  │
  │                     │ pipeline.run(text)  │                      │                  │
  │                     │───────────────────▶│                      │                  │
  │                     │                    │ transcribe_text()    │                  │
  │                     │                    │──────┐               │                  │
  │                     │                    │◀─────┘ Transcript    │                  │
  │                     │                    │                      │                  │
  │                     │                    │ extract(transcript)   │                  │
  │                     │                    │─────────────────────▶│                  │
  │                     │                    │                      │ LLM API call     │
  │                     │                    │                      │──────┐           │
  │                     │                    │                      │◀─────┘ JSON      │
  │                     │                    │     MeetingAnalysis   │                  │
  │                     │                    │◀─────────────────────│                  │
  │                     │                    │                      │                  │
  │                     │                    │ route(analysis)       │                  │
  │                     │                    │─────────────────────────────────────────▶│
  │                     │                    │                      │    RoutingPlan    │
  │                     │                    │◀─────────────────────────────────────────│
  │                     │                    │                      │                  │
  │                     │  AnalyzeResponse   │                      │                  │
  │                     │◀──────────────────│                      │                  │
  │  JSON response      │                    │                      │                  │
  │◀────────────────────│                    │                      │                  │
```

## Appendix B: Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAINFRAME_LLM_API_KEY` | `""` | OpenAI API key (or compatible provider) |
| `MAINFRAME_LLM_MODEL` | `gpt-4o-mini` | Model name |
| `MAINFRAME_LLM_BASE_URL` | `https://api.openai.com/v1` | API base URL (override for DeepSeek etc.) |
| `MAINFRAME_APP_HOST` | `0.0.0.0` | Server bind host |
| `MAINFRAME_APP_PORT` | `8000` | Server bind port |
| `MAINFRAME_DEBUG` | `false` | Debug mode |
