# Connectors (Commercial)

This directory contains commercial connector implementations.

## Structure

```
connectors/
├── im/              # IM integrations (飞书, Slack, etc.)
├── email/           # Email integrations
├── tasks/           # Task system integrations (Jira, Linear)
├── github/          # GitHub/GitLab integrations
└── erp/             # ERP/CRM/WMS integrations
```

## Open Source vs Commercial

| Connector Type | Status | License |
|---------------|--------|---------|
| Basic webhook | Open | Apache 2.0 |
| IM (飞书/Slack) | Commercial | Proprietary |
| Email | Commercial | Proprietary |
| Tasks (Jira/Linear) | Commercial | Proprietary |
| GitHub | Commercial | Proprietary |
| ERP/CRM | Commercial | Proprietary |

## Why Closed Source?

The core Mainframe framework (input, processing, understanding, routing protocol) is open source under Apache 2.0. The connectors—which integrate with specific business systems—are our commercial differentiation.

## Building Your Own Connector

If you'd like to build a custom connector, see the connector protocol specification in `docs/architecture.md`.

## License

Connectors in this directory are proprietary and licensed separately. Contact Le Collectif for commercial licensing.
