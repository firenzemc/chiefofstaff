# chiefofstaff

> The chief of staff for your agents.

Turns conversations into coordinated action — across humans, systems, and agents.

Every conversation ends. Most of what matters doesn't go anywhere. Mainframe is the coordination layer that changes that — receiving what conversations produce, routing each piece to the right place, and following up until there's a result. It doesn't make decisions. It makes sure decisions don't get lost.

---

## The Problem

Meetings are the highest-density decision-making events in any organization. But today, every meeting ends the same way: someone writes notes, someone else forgets to read them, and half the decisions quietly disappear.

The root cause isn't that people are lazy. It's that **there's no system designed to receive what a meeting produces.**

LLMs can now extract decisions, commitments, and open questions from conversation with high accuracy. The missing piece is a coordination layer that knows what to do with them.

That's Mainframe.

---

## What Mainframe Does

When a conversation ends, Mainframe:

1. **Extracts** — pulls structured intent from the transcript: decisions, action items, open questions, data queries, commitments
2. **Classifies** — determines what kind of response each intent requires
3. **Routes** — assigns each item to the right destination:
   - A human who made a commitment → task created and tracked
   - An open question with no owner → agent spawned to research
   - A decision made → written to the relevant system
4. **Audits** — logs every routing decision, surfaces them for human confirmation
5. **Feeds back** — corrections flow back to improve future routing

The conversation is the input. Completed work is the output.

---

## Quickstart

```bash
git clone https://github.com/firenzemc/chiefofstaff
cd chiefofstaff
pip install -e ".[dev]"

# Optional: set your LLM key for real extraction (works without it in mock mode)
export MAINFRAME_LLM_API_KEY=your_openai_key

uvicorn mainframe.main:app --reload
```

Then send a meeting transcript:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "We decided to go with vendor A. Sarah will follow up on the contract by Friday. Still open: do we need a backup supplier?"
  }'
```

Response:

```json
{
  "meeting_id": "meeting-a1b2c3d4",
  "summary": "Vendor A selected. Contract follow-up assigned to Sarah by Friday. Backup supplier question open.",
  "decisions": [{"text": "Go with vendor A", ...}],
  "action_items": [{"text": "Sarah to follow up on contract by Friday", ...}],
  "open_questions": [{"text": "Do we need a backup supplier?", ...}],
  "routes": [
    {"intent_type": "decision", "target": "document", ...},
    {"intent_type": "action_item", "target": "task_tracker", ...},
    {"intent_type": "open_question", "target": "agent", ...}
  ]
}
```

---

## Architecture

```
[ Conversation Input ]
        ↓
  [ Understanding ]     ← intent extraction via LLM (batch or streaming)
        ↓
    [ Router ]          ← rule-based: intent type → target system
        ↓
  ┌─────┴────────┐
  ↓              ↓
[Connectors]  [Agent Coordinator]    ← routes each intent
  IM, tasks,    spawn → supervise
  docs, ERP     → collect results
        ↓
    [ Audit ]           ← human-in-the-loop, execution log
        ↓
   [ Feedback ]         ← corrections → routing improvement
```

```
src/mainframe/
├── main.py             # FastAPI app — POST /analyze, GET /health
├── config.py           # Pydantic settings (MAINFRAME_ env prefix)
├── api/                # Request / response schemas
├── input/              # Adapters: API, file upload, local audio, webhooks
├── processing/         # Transcription (Whisper), speaker diarization
├── understanding/
│   ├── batch/          # Intent extraction pipeline (MVP — ships now)
│   └── streaming/      # Real-time pipeline (Phase 2 — placeholder)
├── router/             # Rule engine: intent type → route target
├── connectors/
│   ├── base.py         # Connector protocol
│   ├── mock.py         # In-memory mock (default)
│   ├── im/             # Feishu, Slack, GitHub, Email   ← open source
│   └── biz/            # ERP, CRM, WMS connectors       ← commercial
├── audit/              # Pipeline run lifecycle, confirmation layer
└── feedback/           # Correction loop → model improvement
```

Each module ships with a `CONTEXT.md` defining its purpose, interfaces, and constraints — readable by agents as well as humans.

---

## Intent Types

| Type | Default Route |
|------|--------------|
| `decision` | Document store |
| `action_item` | Task tracker (with assignee) |
| `open_question` | Agent (research and report back) |
| `commitment` | Task tracker (with due date) |
| `info` | No action |

Routing rules are configurable. The default ruleset lives in `router/default_rules.py`.

---

## Open Source Boundary

| Component | License |
|-----------|---------|
| Core pipeline (understanding, routing, audit) | Apache 2.0 |
| IM connectors (Feishu, Slack, GitHub, Email) | Apache 2.0 |
| Business connectors (ERP, CRM, WMS) | Commercial |
| Industry-specific semantic models | Commercial |

The open-source core runs end-to-end with `MockConnector`. No commercial layer required to get started.

---

## Configuration

All settings use the `MAINFRAME_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAINFRAME_LLM_API_KEY` | — | OpenAI-compatible API key. If unset, falls back to mock extraction |
| `MAINFRAME_LLM_BASE_URL` | `https://api.openai.com/v1` | Base URL for LLM calls |
| `MAINFRAME_LLM_MODEL` | `gpt-4o-mini` | Model used for intent extraction |
| `MAINFRAME_APP_HOST` | `0.0.0.0` | Server host |
| `MAINFRAME_APP_PORT` | `8000` | Server port |
| `MAINFRAME_DEBUG` | `false` | Enable hot reload |

---

## Data Flywheel

Every correction improves the system.

When a human overrides a routing decision — wrong target, missed intent, wrong assignee — that correction feeds back into the model. Over time, Mainframe becomes calibrated to your organization's specific language, domain, and decision patterns.

This is why `feedback/` is built from day one, not bolted on later.

---

## Status

**MVP: batch pipeline** — ships now.

- [x] Intent extraction (LLM + mock fallback)
- [x] Rule-based router
- [x] Audit logger
- [x] FastAPI endpoints (`POST /analyze`, `GET /health`)
- [x] Feedback collector
- [x] 57 tests, 84% coverage
- [ ] Audio input (Whisper) — Phase 2
- [ ] Real connectors (Feishu tasks, GitHub issues) — Phase 2
- [ ] Streaming pipeline — Phase 2

If you're building agent infrastructure and want to contribute a connector or discuss the routing protocol, open an issue.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

*The conversation ended. The work just started.*
