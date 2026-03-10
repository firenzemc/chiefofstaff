"""Tests for RiskAssessor."""

import pytest
from mainframe.audit.risk import RiskAssessor
from mainframe.audit.models import RiskLevel
from mainframe.router.models import RouteResult, RouteTarget
from mainframe.understanding.batch.models import Entity, Intent, IntentType


@pytest.fixture
def assessor():
    return RiskAssessor()


def _make_intent(confidence=0.9, entities=None, intent_type=IntentType.DECISION):
    return Intent(
        id="i1", type=intent_type, content="test", confidence=confidence,
        speaker="Alice", timestamp=1.0, entities=entities or [],
    )


def _make_route(target=RouteTarget.DOCUMENT):
    return RouteResult(
        intent_id="i1", intent_type="decision", target=target, rule_id="r1",
    )


class TestRiskAssessor:
    def test_document_is_low(self, assessor):
        level, _ = assessor.assess(_make_route(RouteTarget.DOCUMENT), _make_intent())
        assert level == RiskLevel.LOW

    def test_task_tracker_is_low(self, assessor):
        level, _ = assessor.assess(_make_route(RouteTarget.TASK_TRACKER), _make_intent())
        assert level == RiskLevel.LOW

    def test_im_message_is_medium(self, assessor):
        level, _ = assessor.assess(_make_route(RouteTarget.IM_MESSAGE), _make_intent())
        assert level == RiskLevel.MEDIUM

    def test_agent_is_medium(self, assessor):
        level, _ = assessor.assess(_make_route(RouteTarget.AGENT), _make_intent())
        assert level == RiskLevel.MEDIUM

    def test_none_is_low(self, assessor):
        level, _ = assessor.assess(_make_route(RouteTarget.NONE), _make_intent())
        assert level == RiskLevel.LOW

    def test_low_confidence_bumps_up(self, assessor):
        level, reason = assessor.assess(
            _make_route(RouteTarget.DOCUMENT),
            _make_intent(confidence=0.5),
        )
        assert level == RiskLevel.MEDIUM
        assert "low_confidence" in reason

    def test_low_confidence_on_medium_bumps_to_high(self, assessor):
        level, _ = assessor.assess(
            _make_route(RouteTarget.IM_MESSAGE),
            _make_intent(confidence=0.5),
        )
        assert level == RiskLevel.HIGH

    def test_money_entity_forces_critical(self, assessor):
        intent = _make_intent(entities=[Entity(type="money", value="$50k")])
        level, reason = assessor.assess(_make_route(RouteTarget.DOCUMENT), intent)
        assert level == RiskLevel.CRITICAL
        assert "critical_entities" in reason

    def test_contract_entity_forces_critical(self, assessor):
        intent = _make_intent(entities=[Entity(type="contract", value="Agreement X")])
        level, _ = assessor.assess(_make_route(RouteTarget.TASK_TRACKER), intent)
        assert level == RiskLevel.CRITICAL

    def test_customer_entity_forces_high(self, assessor):
        intent = _make_intent(entities=[Entity(type="customer", value="ACME Corp")])
        level, _ = assessor.assess(_make_route(RouteTarget.DOCUMENT), intent)
        assert level == RiskLevel.HIGH

    def test_critical_entity_plus_low_confidence(self, assessor):
        intent = _make_intent(confidence=0.5, entities=[Entity(type="payment", value="$10")])
        level, _ = assessor.assess(_make_route(RouteTarget.DOCUMENT), intent)
        # CRITICAL can't bump higher
        assert level == RiskLevel.CRITICAL

    def test_reason_includes_target(self, assessor):
        _, reason = assessor.assess(_make_route(RouteTarget.AGENT), _make_intent())
        assert "target=agent" in reason
