"""
Mock connector for MVP — logs actions instead of executing them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..router.models import RouteResult

logger = logging.getLogger(__name__)


class MockConnector:
    """
    Captures executed routes in memory for inspection/testing.

    Satisfies the ``Connector`` protocol.
    """

    def __init__(self) -> None:
        self.executed: list[dict] = []

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
