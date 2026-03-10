# Phase 2 Technical Assessment: Trust Layer + Memory

> **Author**: dev-lead  
> **Date**: 2026-03-10  
> **Status**: Assessment for chief review

---

## 1. 方向评估

主席提的两个方向我都同意，但**顺序需要调整**。

### 建议的优先级

| # | 方向 | 优先级 | 理由 |
|---|------|--------|------|
| **2A** | Audit 层升级（溯源 + 风险分级 + 回滚） | **P0 — 先做** | 这是 trust 的基础设施，Memory 层也依赖它 |
| **2B** | Memory 层（跨会议承诺追踪） | **P1 — 紧接着做** | 依赖 audit 层的持久化能力 |

### 为什么这个顺序

Memory 层要追踪"3 次会议前的承诺没执行"，前提是每次会议的 intent 都被持久化存储、有唯一 ID、可以跨会议查询。这正是 Audit 升级要做的事。如果先做 Memory 但没有持久化，Memory 只能活在单次进程里，重启就丢，没意义。

### 我对方向的一个修正

主席说的"Audit 升级"和"Memory"其实是一个东西的两面：

- **Audit** = 面向合规/可信的视角：谁做了什么、依据是什么、怎么撤销
- **Memory** = 面向业务智能的视角：跨会议的 pattern 识别、承诺追踪、重复检测

它们共享同一个底层：**持久化的 intent store**。所以我建议先建 store，然后 audit 和 memory 是它上面的两个查询视角。

---

## 2. Phase 2A: Audit 升级 — 详细设计

### 2A.1 当前 Audit 的问题

当前 `audit/models.py` 只记录 pipeline run 级别的信息（开始/结束/成功/失败）。没有：
- 每个 intent 的执行记录
- 溯源链（这个操作来自哪句话）
- 风险等级
- 回滚信息
- 持久化（内存一重启就没了）

### 2A.2 新数据模型

```python
# --- audit/models.py 扩展 ---

class RiskLevel(str, Enum):
    """操作风险等级，决定是否需要人工确认。"""
    LOW = "low"          # 自动执行：记录到文档、发通知
    MEDIUM = "medium"    # 执行后通知人工：创建任务、修改状态
    HIGH = "high"        # 执行前需人工确认：发外部邮件、修改金额、删除
    CRITICAL = "critical"  # 必须人工确认 + 二次确认：涉及资金、合同、客户

class ExecutionStatus(str, Enum):
    PENDING = "pending"           # 等待执行
    AWAITING_APPROVAL = "awaiting_approval"  # 等人工确认
    APPROVED = "approved"         # 人工已确认
    EXECUTED = "executed"         # 已执行
    FAILED = "failed"             # 执行失败
    ROLLED_BACK = "rolled_back"   # 已回滚

class ExecutionRecord(BaseModel):
    """单个 intent 从提取到执行的完整记录。"""
    
    # Identity
    record_id: str
    meeting_id: str
    run_id: str               # 关联到 PipelineRun
    
    # Provenance（溯源）
    intent_id: str
    intent_type: str
    source_speaker: str
    source_text: str          # 原始发言内容
    source_timestamp: float   # 在会议中的时间点
    confidence: float
    
    # Routing
    target: str               # RouteTarget value
    rule_id: str
    payload: dict             # 发给 connector 的数据
    
    # Risk & Approval
    risk_level: RiskLevel
    risk_reason: str = ""     # 为什么是这个风险等级
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Execution
    status: ExecutionStatus = ExecutionStatus.PENDING
    executed_at: Optional[datetime] = None
    execution_result: Optional[dict] = None  # connector 返回的结果
    
    # Rollback
    rollback_hint: str = ""   # 描述如何撤销这个操作
    rolled_back_at: Optional[datetime] = None
    rollback_result: Optional[dict] = None
    
    # Timestamps
    created_at: datetime
```

### 2A.3 风险评估引擎

```python
# --- audit/risk.py (NEW) ---

class RiskAssessor:
    """
    评估每个 routed intent 的风险等级。
    
    规则：
    - RouteTarget.NONE → LOW（纯记录）
    - RouteTarget.DOCUMENT → LOW（写文档可以编辑回来）
    - RouteTarget.IM_MESSAGE → MEDIUM（发出去就收不回来，但影响有限）
    - RouteTarget.TASK_TRACKER → LOW（任务可以关闭/删除）
    - RouteTarget.AGENT → MEDIUM（agent 行为不完全可预测）
    - confidence < 0.7 → 风险上调一级
    - 涉及金额/合同/外部实体 → CRITICAL
    """
    
    def assess(self, route: RouteResult, intent: Intent) -> tuple[RiskLevel, str]:
        ...
```

**关键设计决策**：风险等级是由 (target_type, confidence, entity_types) 三者共同决定的，不是简单的 target→level 映射。低置信度的 decision 比高置信度的 info 更危险。

### 2A.4 回滚提示（Rollback Hint）

每种 target 有不同的回滚策略：

| Target | Rollback Hint 示例 |
|--------|-------------------|
| DOCUMENT | `"DELETE paragraph at section 'Decisions' containing 'Launch next week'"` |
| TASK_TRACKER | `"CLOSE task ID={task_id} created for '{title}'"` |
| IM_MESSAGE | `"UNSEND message ID={msg_id} in channel {channel}"` — 注意：多数 IM 不支持撤回 |
| AGENT | `"CANCEL agent run ID={agent_run_id}"` |

回滚不是自动执行的。`rollback_hint` 是给人或给 agent 看的指令，实际回滚由 connector 的 `rollback()` 方法执行（需要人确认）。

### 2A.5 持久化方案

MVP 阶段用 SQLite（本地文件，零运维）：

```python
# --- audit/store.py (NEW) ---

class AuditStore:
    """SQLite-backed persistent audit store."""
    
    def __init__(self, db_path: str = "mainframe_audit.db"):
        ...
    
    async def save_execution(self, record: ExecutionRecord) -> None: ...
    async def get_by_meeting(self, meeting_id: str) -> list[ExecutionRecord]: ...
    async def get_by_status(self, status: ExecutionStatus) -> list[ExecutionRecord]: ...
    async def get_pending_approvals(self) -> list[ExecutionRecord]: ...
    async def update_status(self, record_id: str, status: ExecutionStatus, **kwargs) -> None: ...
```

**为什么 SQLite 不是 PostgreSQL**：
1. "业务逻辑变代码在本地执行" — Chao 明确要求本地运行
2. 零运维，不需要额外进程
3. 单写者够用（这不是高并发场景）
4. 以后需要换 PG 只要换 store 实现，接口不变

### 2A.6 对现有代码的影响

| 文件 | 变更 |
|------|------|
| `audit/models.py` | 新增 RiskLevel, ExecutionStatus, ExecutionRecord |
| `audit/risk.py` | **新增** — 风险评估引擎 |
| `audit/store.py` | **新增** — SQLite 持久化 |
| `audit/logger.py` | 扩展：记录 ExecutionRecord，不只是 PipelineRun |
| `router/engine.py` | route() 返回值需要携带 source_text 和 source_timestamp |
| `router/models.py` | RouteResult 添加 source_text, source_timestamp, risk_level 字段 |
| `main.py` | /analyze 流程中插入 risk assessment 和 approval gate |
| `connectors/base.py` | Connector protocol 添加 rollback() 方法 |
| `pyproject.toml` | 添加 `aiosqlite` 依赖 |

**预估新增代码**：~500 行生产 + ~300 行测试

---

## 3. Phase 2B: Memory 层 — 详细设计

### 3B.1 核心问题

Memory 要回答的问题：
1. "这个 action_item 在之前的会议里出现过吗？" → **重复检测**
2. "张三上次承诺的事情做了吗？" → **承诺追踪**
3. "这个供应商上次延误了几天？" → **实体历史查询**
4. "过去 3 次会议的未关闭项有哪些？" → **跨会议聚合**

### 3B.2 数据模型

```python
# --- memory/models.py (NEW) ---

class CommitmentStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class Commitment(BaseModel):
    """跨会议追踪的承诺/行动项。"""
    commitment_id: str
    
    # 内容
    content: str              # "准备文档"
    owner: str                # "Bob"
    due_date: Optional[str]   # "Friday"
    
    # 来源
    source_meeting_id: str
    source_intent_id: str
    source_text: str          # 原话
    
    # 追踪
    status: CommitmentStatus = CommitmentStatus.OPEN
    first_seen_at: datetime
    last_mentioned_at: datetime
    mention_count: int = 1    # 在多少次会议中被提到
    mention_meetings: list[str] = []  # 哪些会议提到了
    
    # 关闭
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    closed_evidence: Optional[str] = None  # 什么证据表明它完成了

class EntityMemory(BaseModel):
    """实体的历史记忆。"""
    entity_type: str          # "supplier", "person", "project"
    entity_value: str         # "供应商A"
    
    facts: list[dict]         # [{meeting_id, fact, timestamp}]
    # 例：[{meeting: "m1", fact: "延误3天", ts: ...}, {meeting: "m3", fact: "又延误", ts: ...}]
```

### 3B.3 跨会议匹配

新会议的 intent 提取完成后，Memory 层做两件事：

1. **匹配已有承诺**：对每个 ACTION_ITEM/COMMITMENT，检查是否有语义相似的 open commitment
2. **更新实体记忆**：对每个 entity，追加到实体历史

匹配逻辑（MVP 用简单文本相似度，不引入向量数据库）：

```python
class CommitmentMatcher:
    """匹配新 intent 和已有的 open commitments。"""
    
    def match(self, new_intent: Intent, open_commitments: list[Commitment]) -> Optional[Commitment]:
        """如果新 intent 和某个已有承诺匹配，返回那个承诺。"""
        # MVP: owner 相同 + 内容关键词重叠 > 50%
        # Phase 3: 用 embedding 做语义匹配
        ...
```

### 3B.4 对 Pipeline 的影响

```
POST /analyze (现有流程)
     │
     ├── 1. Transcribe
     ├── 2. Extract intents (LLM)
     ├── 3. Route intents
     ├── 4. Risk assess          ← Phase 2A 新增
     ├── 5. Memory check         ← Phase 2B 新增
     │   ├── 匹配已有承诺 → 更新 mention_count
     │   ├── 识别重复项 → 标记 "repeated, first seen in meeting X"
     │   └── 更新实体记忆
     ├── 6. Execute (or await approval)
     └── 7. Audit log
```

### 3B.5 API 新增

```python
# 查询未关闭的承诺
GET /commitments?status=open&owner=Bob

# 查询实体历史
GET /memory/entity?type=supplier&value=供应商A

# 查询重复项
GET /commitments/repeated?min_mentions=2
```

**预估新增代码**：~400 行生产 + ~250 行测试

---

## 4. 总体实现计划

### Phase 2A 任务拆解（Audit 升级）

| Task | 内容 | 行数 | 依赖 |
|------|------|------|------|
| 2A-1 | 新增 ExecutionRecord, RiskLevel 等模型 | ~80 | 无 |
| 2A-2 | RiskAssessor 风险评估引擎 | ~100 | 2A-1 |
| 2A-3 | AuditStore SQLite 持久化 | ~150 | 2A-1 |
| 2A-4 | 扩展 RouteResult 携带溯源信息 | ~40 | 2A-1 |
| 2A-5 | Connector protocol 添加 rollback | ~30 | 2A-1 |
| 2A-6 | main.py 集成 risk gate + execution recording | ~80 | 2A-1~5 |
| 2A-7 | 测试 | ~300 | 2A-1~6 |

### Phase 2B 任务拆解（Memory 层）

| Task | 内容 | 行数 | 依赖 |
|------|------|------|------|
| 2B-1 | Commitment + EntityMemory 模型 | ~70 | 2A-3 (store) |
| 2B-2 | MemoryStore SQLite 持久化 | ~120 | 2A-3 |
| 2B-3 | CommitmentMatcher 匹配引擎 | ~80 | 2B-1 |
| 2B-4 | Pipeline 集成 memory check | ~60 | 2B-1~3 |
| 2B-5 | API endpoints (GET /commitments, /memory) | ~70 | 2B-1~4 |
| 2B-6 | 测试 | ~250 | 2B-1~5 |

### 时间估算

- **2A**: 可以并行分给 dev-exec (2A-1~5) 和 dev-test (2A-7 设计)
- **2B**: 在 2A 完成后启动，2B-1~3 可以和 2A-6 并行

---

## 5. 我认为有一件事比 2A/2B 更紧急

**Push MVP 代码到 GitHub。**

现在 57 个测试全部通过，但代码还在本地。Phase 2 的工作量大（~1450 行），如果在 Phase 2 过程中出问题，没有 git 历史可以回退。

**建议**：先 push Phase 1 到 main branch（或 feature branch），然后 Phase 2 在新 branch 上开发。

---

## 6. 对主席方向的总结

| 主席的需求 | 技术实现 | 评估 |
|-----------|---------|------|
| 每个 AI 操作可溯源 | ExecutionRecord.source_* 字段 | ✅ 直接覆盖 |
| 可回滚 | rollback_hint + Connector.rollback() | ✅ 描述性回滚，Phase 3 做自动回滚 |
| 风险分级人工确认 | RiskAssessor + ExecutionStatus.AWAITING_APPROVAL | ✅ 避免审批疲劳 |
| 承诺追踪（忘了的事） | Commitment model + CommitmentMatcher | ✅ MVP 用关键词匹配 |
| 数据隐私/本地执行 | SQLite + 本地 LLM 支持 (base_url 可配) | ✅ 已支持 |

**方向完全合理。没有我认为更重要的事先做——除了 push。**
