# Connectors Module

## What this does
Integrates with external systems to execute routed actions.

## Why it exists
Different targets need different integration implementations.

## Open Source (Apache 2.0)

```
connectors/im/
├── feishu.py    # 飞书 messages + tasks
├── slack.py     # Slack messages + channels
├── github.py    # GitHub issues + PRs
└── email.py     # Email via SMTP
```

## Commercial (Closed)

```
connectors/biz/
├── wangdiantong.py   # 旺店通 WMS
├── jushuitan.py      # 聚水潭 WMS
└── jindie.py         # 金蝶 ERP
```

## Why split this way?

IM and GitHub integrations are通用 enough to open-source. Business system integrations are our commercial differentiation.

## Interfaces

```python
class Connector(Protocol):
    async def connect(self) -> None: ...
    async def send(self, action: Action) -> Result: ...
    async def disconnect(self) -> None: ...
```
