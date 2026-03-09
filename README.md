# mainframe

> Intent routing for the agentic era.

**If IFTTT connected apps, Mainframe connects conversations to agents.**

---

## What is this?

Mainframe is an **intent routing engine**. It listens to human conversations, extracts structured intent, and routes it to the right agents and systems—automatically.

The upstream can be anything: a meeting, a voice memo, a Slack thread, an email. The downstream can be anything: a task system, a CRM, a GitHub repo, an ERP. The core is the routing layer in between.

```
[ Conversation ] → [ Intent Extraction ] → [ Router ] → [ Agent / System ]
```

This is the missing infrastructure layer for the agentic era. LLMs are getting better at acting. What's missing is a reliable way to turn human conversation into structured agent instructions.

---

## The Problem

Every organization runs agents today—ERP agents, CRM agents, AI assistants. But they're all blind to the highest-density source of human intent: **conversation**.

Decisions are made in meetings. Commitments are made in calls. Priorities are set in Slack threads. None of it reaches your agents automatically. Someone has to manually bridge the gap—and most of the time, they don't.

Mainframe closes this loop.

---

## How It Works

1. **Ingest** — Connect any conversation source (meeting audio, voice memo, chat transcript, API stream)
2. **Understand** — Extract structured intent: decisions, action items, queries, commitments, open questions
3. **Route** — Match intent to target: which agent, which system, which person
4. **Deliver** — Write to the right place: task created, CRM updated, GitHub issue opened, message sent
5. **Learn** — Every human correction feeds back into routing accuracy for your domain

---

## Use Cases

### Meetings → Action
The highest-signal use case. A 1-hour meeting produces dozens of intents. Mainframe routes all of them without anyone taking notes.

### Voice Memo → Task
Record a thought on the way to work. Mainframe extracts the intent and creates the task before you sit down.

### Support Call → CRM
Customer says "I need this by Friday." Mainframe writes it to the CRM. No manual entry.

### Engineering Sync → GitHub
"Let's file a bug for that." Mainframe opens the issue. Assigns it. Labels it.

---

## Architecture

```
src/mainframe/
├── input/          # Adapters: local mic, system audio, API, file upload
├── processing/     # Transcription (Whisper), speaker diarization
├── understanding/  # Intent extraction: batch pipeline + streaming (WIP)
├── router/         # Intent → target mapping, rules engine
├── connectors/
│   ├── im/         # Feishu, Slack, GitHub, Email  ← open source
│   └── biz/        # ERP, CRM, WMS connectors      ← commercial
├── audit/          # Human-in-the-loop confirmation, execution log
└── feedback/       # Correction loop → model improvement
```

Each module ships with a `CONTEXT.md` explaining its purpose, interfaces, and constraints. Designed for agents and humans alike.

---

## Open Source Boundary

| Component | License |
|-----------|---------|
| Core engine (input → understanding → router → audit) | Apache 2.0 |
| IM connectors (Feishu, Slack, GitHub, Email) | Apache 2.0 |
| Business connectors (ERP, CRM, WMS) | Commercial |
| Industry semantic models | Commercial |

The open-source core is fully functional end-to-end. You can run Mainframe with any IM connector without touching the commercial layer.

---

## Data Flywheel

The real moat is not the architecture. It's what happens after deployment.

Every time a human corrects a routing decision—wrong target, wrong intent label, missed commitment—that correction feeds back into the model. Over time, Mainframe gets calibrated to your organization's specific language, domain, and decision patterns.

This is why `src/mainframe/feedback/` is built from day one, not added later.

---

## Design Principles

- **Conversation-first**: Routing logic is designed around natural language, not structured inputs
- **Human-in-the-loop by default**: Audit layer ships enabled; automation is opt-in
- **Upstream/downstream agnostic**: Core protocol doesn't care what's on either end
- **Agent-friendly codebase**: CONTEXT.md per module, Pydantic contracts, <300 lines/file

---

## Quick Start

```bash
pip install -e ".[dev]"
# see docs/quickstart.md
```

---

## Status

Early development. Architecture is stable. MVP batch pipeline in progress.

If you're building in this space or want to contribute a connector, open an issue.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

*The conversation happened. Make sure it mattered.*
