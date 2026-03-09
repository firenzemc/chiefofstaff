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
