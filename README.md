# chiefofstaff

> The chief of staff for your agents.

Turns conversations into coordinated action — across humans, systems, and agents.

Every meeting ends. Most decisions don't go anywhere. Mainframe is the coordination layer that changes that — receiving what conversations produce, routing each piece to the right place, and following up until there's a result. It doesn't make decisions. It makes sure decisions don't get lost.

---

## The Problem

Meetings are the highest-density decision-making events in any organization. But today, every meeting ends the same way: someone writes notes, someone else forgets to read them, and half the decisions quietly disappear.

The root cause isn't that people are lazy. It's that **there's no system designed to receive what a meeting produces.**

LLMs can now extract decisions, commitments, and open questions from conversation with high accuracy. The missing piece is an coordination layer that knows what to do with them.

That's Mainframe.

---

## What Mainframe Does

When a conversation ends, Mainframe:

1. **Extracts** — pulls structured intent from the transcript: decisions, action items, open questions, data queries, commitments
2. **Classifies** — determines what kind of response each intent requires
3. **Routes** — assigns each item to the right destination:
   - A human who made a commitment
   - An external system (CRM, ERP, task tracker)
   - An agent that can execute or research autonomously
4. **Coordinates** — spawns and supervises agents as needed, waits for results, handles failures
5. **Closes the loop** — surfaces results back to the relevant people and systems

The conversation is the input. Completed work is the output.

---

## Agent-Native Design

Mainframe is built for a world where agents are first-class participants in organizational work.

- **Conversations spawn agents**: When a meeting produces an open question or a research task with no clear human owner, Mainframe can spawn an agent to handle it—not create a to-do that sits in a backlog.
- **Agents can call Mainframe**: Other agents in your system can use Mainframe's routing protocol to dispatch work that originates from conversation, not just from code.
- **Supervision is built in**: Spawned agents report back through Mainframe's audit layer. Nothing disappears silently.

This is what separates an coordinator from a router. A router sends a message. An coordinator owns the outcome.

---

## The Meeting Use Case

Meetings are the canonical use case—and the hardest one.

A 1-hour meeting produces dozens of intents. Traditional meeting tools turn these into a notes document. Mainframe turns them into:

| Intent Type | What Happens |
|------------|--------------|
| Decision made | Written to the relevant system (CRM, ERP, doc) |
| Commitment by a person | Task created, assigned, tracked |
| Open question with no owner | Agent spawned to research and report back |
| Data query raised | Lookup triggered, result surfaced in context |
| Follow-up needed with someone external | Draft prepared, human confirms before send |

The meeting ends. Mainframe keeps working.

---

## Architecture

```
[ Conversation Input ]
        ↓
  [ Understanding ]     ← intent extraction, entity recognition, context
        ↓
    [ Router ]          ← classification, target resolution, priority
        ↓
  ┌─────┴──────┐
  ↓            ↓
[ Connectors ] [ Agent Coordinator ]
  IM, CRM,       spawn → supervise → collect
  ERP, Git       → surface results
        ↓
    [ Audit ]           ← human-in-the-loop, execution log
        ↓
   [ Feedback ]         ← corrections → model improvement
```

```
src/mainframe/
├── input/          # Adapters: API stream, file upload, local audio, webhooks
├── processing/     # Transcription, speaker diarization
├── understanding/  # Intent extraction: batch + streaming
├── router/         # Target resolution, rules engine
├── connectors/
│   ├── im/         # Feishu, Slack, GitHub, Email      ← open source
│   └── biz/        # ERP, CRM, WMS connectors          ← commercial
├── audit/          # Confirmation layer, execution log
└── feedback/       # Correction loop → routing improvement
```

Each module ships with a `CONTEXT.md` defining its purpose, interfaces, and constraints—designed to be readable by agents as well as humans.

---

## Open Source Boundary

| Component | License |
|-----------|---------|
| Core coordination engine | Apache 2.0 |
| IM connectors (Feishu, Slack, GitHub, Email) | Apache 2.0 |
| Business connectors (ERP, CRM, WMS) | Commercial |
| Industry-specific semantic models | Commercial |

The open-source core runs end-to-end. No commercial layer required to get started.

---

## Data Flywheel

Every correction improves the system.

When a human overrides a routing decision—wrong target, missed intent, wrong agent assigned—that correction feeds back into the model. Over time, Mainframe becomes calibrated to your organization's specific language, domain, and decision patterns.

This is why `feedback/` is built from day one.

---

## Status

Early development. Core architecture is stable. MVP batch pipeline in progress.

If you're building agent infrastructure and want to contribute a connector or discuss the routing protocol, open an issue.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

*The meeting ended. The work just started.*
