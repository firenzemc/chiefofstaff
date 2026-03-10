"""
Risk assessment engine.

Evaluates each routed intent and assigns a risk level based on
target type, confidence score, and entity characteristics.
"""

from __future__ import annotations

from ..router.models import RouteResult, RouteTarget
from ..understanding.batch.models import Intent
from .models import RiskLevel


# Confidence threshold below which risk is bumped up one level.
_LOW_CONFIDENCE_THRESHOLD = 0.7

# Entity types that force CRITICAL risk regardless of target.
_CRITICAL_ENTITY_TYPES = frozenset({
    "money", "amount", "contract", "payment", "invoice",
})

# Entity types that force at least HIGH risk.
_HIGH_ENTITY_TYPES = frozenset({
    "external_email", "customer", "legal", "deadline",
})

# Base risk per route target.
_TARGET_BASE_RISK: dict[str, RiskLevel] = {
    RouteTarget.NONE.value: RiskLevel.LOW,
    RouteTarget.DOCUMENT.value: RiskLevel.LOW,
    RouteTarget.TASK_TRACKER.value: RiskLevel.LOW,
    RouteTarget.IM_MESSAGE.value: RiskLevel.MEDIUM,
    RouteTarget.AGENT.value: RiskLevel.MEDIUM,
}

# Ordered severity for bump logic.
_SEVERITY_ORDER: list[RiskLevel] = [
    RiskLevel.LOW,
    RiskLevel.MEDIUM,
    RiskLevel.HIGH,
    RiskLevel.CRITICAL,
]


def _bump(level: RiskLevel, steps: int = 1) -> RiskLevel:
    """Increase risk level by *steps*, capping at CRITICAL."""
    idx = _SEVERITY_ORDER.index(level)
    return _SEVERITY_ORDER[min(idx + steps, len(_SEVERITY_ORDER) - 1)]


class RiskAssessor:
    """
    Stateless risk evaluator.

    Risk is determined by three dimensions:
    1. **Target type** — writing a doc is safer than sending an IM.
    2. **Confidence** — low-confidence decisions are riskier.
    3. **Entities** — mentions of money/contracts force higher risk.
    """

    def assess(self, route: RouteResult, intent: Intent) -> tuple[RiskLevel, str]:
        """
        Return ``(risk_level, reason)`` for a routed intent.
        """
        reasons: list[str] = []

        # 1. Base risk from target
        level = _TARGET_BASE_RISK.get(route.target.value, RiskLevel.MEDIUM)
        reasons.append(f"target={route.target.value}")

        # 2. Entity escalation
        entity_types = {e.type.lower() for e in intent.entities}

        if entity_types & _CRITICAL_ENTITY_TYPES:
            level = RiskLevel.CRITICAL
            matched = entity_types & _CRITICAL_ENTITY_TYPES
            reasons.append(f"critical_entities={matched}")
        elif entity_types & _HIGH_ENTITY_TYPES:
            if _SEVERITY_ORDER.index(level) < _SEVERITY_ORDER.index(RiskLevel.HIGH):
                level = RiskLevel.HIGH
            matched = entity_types & _HIGH_ENTITY_TYPES
            reasons.append(f"high_risk_entities={matched}")

        # 3. Low-confidence bump
        if intent.confidence < _LOW_CONFIDENCE_THRESHOLD:
            level = _bump(level)
            reasons.append(f"low_confidence={intent.confidence:.2f}")

        return level, "; ".join(reasons)
