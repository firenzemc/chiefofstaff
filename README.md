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

---

## Key Differentiators

### 1. Local Microphone Capture
The only solution for in-person meetings—no cloud recording required.

### 2. System Audio Loopback
No platform recording permissions needed—captures directly from system audio.

### 3. Streaming + Batch Dual Mode
- **Streaming**: Real-time intent inference (low latency)
- **Batch**: Post-meeting full analysis (high accuracy, human-correctable)

### 4. GitHub Integration
Technical team decisions automatically become GitHub issues or PRs.

---

## Architecture

```
INPUT → PROCESSING → UNDERSTANDING → ROUTER → CONNECTORS → AUDIT
         ↓              ↓              ↓           ↓            ↓
    Local Mic      Whisper      Intent      Rules      IM/Email
    Loopback       Diarize      Extraction  Targets    Tasks/Git
    API            Chunking     Context     Triggers   ERP/CRM
```

---

## Open Source / Commercial Split

### Apache 2.0 (This Repo)

- Input adapters (local, API, upload)
- Processing pipeline (Whisper, diarization)
- Intent extraction framework
- Routing protocol
- Audit interface
- **IM Connectors** (飞书, Slack, GitHub, Email)

### Commercial (Closed)

- Business system connectors (旺店通, 聚水潭, 金蝶)
- Industry-specific semantic models

---

## Data Flywheel

> The real moat is not the architecture—it's the data flywheel.

Every human correction feeds back into improving intent recognition accuracy for your specific domain.

---

## Quick Start

```bash
pip install -e .
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

**The meeting is over. The work begins.**
