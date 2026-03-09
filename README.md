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

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MAINFRAME                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│  │   INPUT     │    │  PROCESS   │    │ UNDERSTAND │              │
│  ├─────────────┤    ├─────────────┤    ├─────────────┤              │
│  │ • Feishu    │    │ • Whisper   │    │ • LLM       │              │
│  │ • Zoom      │───▶│ • Diarize  │───▶│ • Intent    │              │
│  │ • Upload    │    │ • Segment  │    │ • Extract   │              │
│  └─────────────┘    └─────────────┘    └──────┬──────┘              │
│                                                │                     │
│  ┌─────────────┐    ┌─────────────┐           │                     │
│  │   AUDIT     │◀───│   ROUTER    │◀──────────┤                     │
│  ├─────────────┤    ├─────────────┤    ┌──────▼──────┐             │
│  │ • Records   │    │ • Rules    │    │ • Connectors│             │
│  │ • Approvals │◀───│ • Agent Map │───▶│ • Webhooks │             │
│  │ • Trace     │    │ • Triggers │    │ • APIs     │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### The Core Pipeline

```
Human Meeting (audio/video) 
          ↓
    ┌─────────────────────┐
    │    Mainframe        │
    │  Capture →          │
    │  Understand →       │
    │  Route →            │
    │  Close the loop    │
    └─────────────────────┘
          ↓           ↓           ↓
    Business    Personal    Knowledge
    Agent       Agent       Base
    (ERP/CRM)  (Tasks)     (Decisions)
```

---

## Open Source / Commercial Split

### Apache 2.0 Licensed (This Repo)

The core infrastructure—the parts that define *how* meetings become actions:

- **Transcription Pipeline** — Whisper integration, speaker diarization
- **Intent Extraction Framework** — LLM-based structured extraction
- **Routing Protocol** — Rule engine, agent mapping
- **Audit Interface** — Execution logging, approval workflows

### Commercial (Closed Source)

Where our differentiation lives:

- **ERP Connectors** — WMS, ERP, CRM integrations
- **Industry Models** — Domain-specific semantic understanding
- **Enterprise Features** — SSO, audit compliance, SLA

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

- [ ] **Phase 1**: Audio → Structured Action Map (no integrations)
- [ ] **Phase 2**: System integrations (ERP, CRM, WMS)  
- [ ] **Phase 3**: Real-time meeting copilot

---

## Philosophy

> "The meeting ended" shouldn't mean "the decision disappeared."

We believe:

1. **Meetings are the highest-signal data source in any company.** Every bug report, feature request, customer complaint, and strategic decision passes through a meeting.

2. **The gap between meeting and system is a trillion-dollar problem.** Companies spend billions on ERP, CRM, and "AI assistants"—but the bridge between human conversation and these systems is broken.

3. **Open core wins.** The routing protocol should be transparent. The integrations should be competitive moats.

4. **Agents will eventually maintain agents.** Once Mainframe routes decisions correctly, agents will start closing their own loops. The future is agents auditing agents.

---

## Contributing

Contributions welcome. This is an early-stage project—architecture opinions strongly encouraged.

```
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
