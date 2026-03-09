# GitHub Connector

> Code connector for GitHub

## What this does
Creates issues and PRs from meeting decisions.

## Why it exists
Technical teams make decisions in meetings. Those decisions should become tracked work items in the repo—no copy-paste needed.

## Interfaces

```python
from pydantic import BaseModel

class GitHubIssue(BaseModel):
    repo: str
    owner: str
    title: str
    body: str
    labels: List[str] = []

class GitHubPR(BaseModel):
    repo: str
    owner: str
    title: str
    head: str
    base: str
    body: str

class GitHubConnector:
    async def create_issue(self, issue: GitHubIssue) -> str: ...
    async def create_pr(self, pr: GitHubPR) -> str: ...
```
