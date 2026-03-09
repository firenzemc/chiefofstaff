# mainframe

> The meeting layer for multi-agent systems.

**One-liner:** Every meeting is a decision. Most are lost. Mainframe routes them.

---

## What is this?

Mainframe is **not** a meeting notes tool. It's a message bus for multi-agent systems where the source of truth is human conversation.

While every company runs three types of agents today—business agents (ERP, CRM), personal agents (AI assistants), and the meetings themselves—there's a fundamental disconnect: **decisions are made in meetings but disappear the moment the meeting ends.**

Mainframe bridges this gap. It captures, understands, and routes every decision, query, and commitment from your meetings to the right systems and agents.

---

## The Problem

| Agent Type | Examples | Knows | Doesn't Know |
|-----------|----------|-------|--------------|
| **Business Agent** | ERP, CRM, WMS | System state, history | What's being decided in meetings |
| **Personal Agent** | Your AI assistant | Your tasks, context | The meeting's full context |
| **Meeting Itself** | Voice, video, discussion | Every decision and intent | How to write to systems |

**Meeting is the highest-density decision-making event in any organization. But it's also the biggest blind spot in your agent infrastructure.**

Decisions are born in meetings. They die in the minutes after.

---

## Key Differentiators

### 1. Local Microphone Capture — The Only Solution for In-Person Meetings

Every other product requires cloud recording or platform API access. Mainframe captures directly from local mic—for offline meetings, interviews, and field conversations.

### 2. System Audio Loopback — No Platform Recording Permissions

Don't want to ask IT for Zoom/Teams recording permissions? Mainframe can capture system audio directly—no cloud dependency, no admin approval needed.

### 3. Streaming + Batch Dual Mode

- **Streaming**: Real-time intent inference with small models (low latency)
- **Batch**: Full post-meeting analysis with large models (high accuracy, human-correctable)

Both modes coexist. Real-time for immediate alerts, batch for precision.

### 4. GitHub Integration

Technical team decisions? Meeting outcomes automatically become GitHub issues or PRs. No copy-paste between Slack and repo.

---

## Architecture

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

### Target Routes

| Target | Examples |
|--------|----------|
| **IM** | 飞书, 企业微信, Slack |
| **Email** | Gmail, Outlook, 企业邮箱 |
| **Tasks** | 飞书任务, Jira, Linear |
| **Code** | GitHub Issues, GitLab MR |
| **Business** | ERP, CRM, WMS |

---

## Directory Structure

```
mainframe/
├── src/mainframe/
│   ├── input/              # Input adapters
│   │   ├── api/            # Feishu, Zoom webhook
│   │   ├── local/          # Mic capture, loopback
│   │   └── upload/         # File upload
│   ├── processing/         # Audio processing
│   │   ├── transcription/  # Whisper
│   │   └── diarization/   # Speaker separation
│   ├── understanding/     # Intent extraction
│   │   ├── streaming/      # Real-time inference
│   │   └── batch/         # Post-meeting analysis
│   ├── router/            # Routing engine
│   ├── connectors/        # (Commercial, closed)
│   └── audit/             # Logging & compliance
├── docs/
├── tests/
└── examples/
```

---

## Open Source / Commercial Split

### Apache 2.0 Licensed (This Repo)

The core infrastructure:

- **Input Adapters** — Local mic, loopback, API, upload
- **Transcription Pipeline** — Whisper integration, diarization
- **Intent Extraction Framework** — Streaming + batch LLM extraction
- **Routing Protocol** — Rule engine, agent mapping
- **Audit Interface** — Execution logging, approval workflows

### Commercial (Closed Source)

Our differentiation:

- **IM Connectors** — 飞书, 企业微信, Slack (beyond basic)
- **GitHub Integration** — Issues, PRs, Projects
- **ERP Connectors** — WMS, ERP, CRM integrations
- **Industry Models** — Domain-specific semantic understanding

---

## Why This Matters

### The 80s mainframe is back.

In the mainframe era, one machine connected everything. Then we fragmented into silos—CRM here, ERP there, personal tools everywhere.

**Now AI is reconnecting them.**

But the missing piece? **The meeting room.** It's where the most important decisions get made, yet it's a black hole to every agent system in your company.

Mainframe brings the mainframe philosophy to the agent era: **one system to route intent to action, across every tool your company uses.**

---

## Quick Start

```bash
# Coming soon
```

---

## Roadmap

- [ ] **Phase 1**: Local mic + Whisper → Structured Action Map
- [ ] **Phase 2**: Streaming intent inference + batch refinement
- [ ] **Phase 3**: IM, Email, Task integrations
- [ ] **Phase 4**: GitHub connector + real-time copilot
- [ ] **Phase 5**: Enterprise ERP/CRM integrations

---

## Philosophy

> "The meeting ended" shouldn't mean "The decision disappeared."

We believe:

1. **Meetings are the highest-signal data source in any company.** Every bug report, feature request, customer complaint, and strategic decision passes through a meeting.

2. **The gap between meeting and system is a trillion-dollar problem.** Companies spend billions on ERP, CRM, and "AI assistants"—but the bridge between human conversation and these systems is broken.

3. **In the AI era, the half-life of technical knowledge is ~18 months.** That's why we open-source the architecture layer—protocols should be community-owned, while integrations are our competitive moat.

4. **One day, agents will maintain agents.** Once Mainframe routes decisions correctly, agents will start auditing each other. The future is agents monitoring agents. We're building the protocol for that future.

5. **Local-first, cloud-optional.** Your meeting data shouldn't need to go to the cloud just to be understood. Process locally when possible, route globally when needed.

---

## Contributing

Contributions welcome. This is an early-stage project—architecture opinions strongly encouraged.

```bash
git clone git@github.com:firenzemc/mainframe.git
cd mainframe
pip install -e .
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

---

## Contact

- Website: (coming soon)
- Email: (coming soon)

---

**The meeting is over. The work begins.**
