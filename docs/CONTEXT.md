# mainframe Project Context

## What this project is

Mainframe is a message bus for multi-agent systems, bridging human meetings and automated agents. The core value: **decisions made in meetings should flow to the right systems, not disappear.**

## Why it exists

Three types of agents exist in modern enterprises:
- Business agents (ERP, CRM)
- Personal agents (AI assistants)  
- The meeting itself

But there's a gap—decisions made in meetings don't automatically reach these agents. Mainframe fills that gap.

## Key principles

1. **Agent-friendly code** — Maintainers of tomorrow may be AI agents
2. **Open core** — Architecture open, integrations commercial
3. **Local-first** — Process locally when possible, route globally when needed

## Directory structure

```
src/mainframe/
├── input/           # Data ingestion
├── processing/      # Audio processing
├── understanding/   # Intent extraction (core)
├── router/          # Decision routing
├── connectors/      # Output integrations
├── audit/          # Logging & compliance
└── feedback/       # Data flywheel
```
