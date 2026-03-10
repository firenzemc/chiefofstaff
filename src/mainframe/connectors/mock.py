"""
Mock connector for MVP — logs actions instead of executing them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..router.models import RouteResult, RouteTarget

logger = logging.getLogger(__name__)

# Rollback hint templates per target type.
_ROLLBACK_HINTS: dict[str, str] = {
    RouteTarget.TASK_TRACKER.value: "CLOSE task '{title}' assigned to {assignee}",
    RouteTarget.DOCUMENT.value: "DELETE paragraph in section '{section}' containing '{content}'",
    RouteTarget.IM_MESSAGE.value: "UNSEND message containing '{content}' (may not be supported)",
    RouteTarget.AGENT.value: "CANCEL agent run for query '{query}'",
    RouteTarget.NONE.value: "No action to rollback",
}


class MockConnector:
    """
    Captures executed routes in memory for inspection/testing.

    Satisfies the ``Connector`` protocol (execute + rollback).
    """

    def __init__(self) -> None:
        self.executed: list[dict] = []
        self.rolled_back: list[dict] = []

    async def execute(self, route: RouteResult) -> dict:
        """Record the route and return a mock-success result."""
        record = {
            "intent_id": route.intent_id,
            "target": route.target.value,
            "rule_id": route.rule_id,
            "payload": route.payload,
            "status": "mock_ok",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.executed.append(record)
        logger.info("MockConnector executed route %s → %s", route.intent_id, route.target.value)
        return record

    async def rollback(self, route: RouteResult, execution_result: dict) -> dict:
        """Record a mock rollback."""
        record = {
            "intent_id": route.intent_id,
            "target": route.target.value,
            "status": "mock_rolled_back",
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
        }
        self.rolled_back.append(record)
        logger.info("MockConnector rolled back %s", route.intent_id)
        return record

    @staticmethod
    def build_rollback_hint(route: RouteResult) -> str:
        """Generate a human-readable rollback hint for a route."""
        template = _ROLLBACK_HINTS.get(route.target.value, "Manual rollback required")
        # Merge payload + provenance, with provenance as fallback for missing keys
        fmt_vars = {**route.payload}
        fmt_vars.setdefault("content", route.source_text[:80] if route.source_text else "")
        fmt_vars.setdefault("title", route.source_text[:80] if route.source_text else "")
        fmt_vars.setdefault("assignee", route.source_speaker or "unknown")
        fmt_vars.setdefault("section", "General")
        fmt_vars.setdefault("query", route.source_text[:80] if route.source_text else "")
        try:
            return template.format(**fmt_vars)
        except (KeyError, IndexError):
            return f"Rollback: undo {route.target.value} for intent {route.intent_id}"
