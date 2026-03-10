"""
Connector protocol — defines the interface all connectors must implement.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..router.models import RouteResult


@runtime_checkable
class Connector(Protocol):
    """Protocol that every connector must satisfy."""

    async def execute(self, route: RouteResult) -> dict:
        """Execute a routed action and return a result dict."""
        ...

    async def rollback(self, route: RouteResult, execution_result: dict) -> dict:
        """
        Attempt to reverse a previously executed action.

        Args:
            route: The original route that was executed.
            execution_result: The result dict from the original execute() call.

        Returns:
            A result dict describing the rollback outcome.
        """
        ...
