"""
Shared test fixtures for the mainframe test suite.
"""

import pytest

from mainframe.understanding.batch.models import (
    ActionItem,
    Entity,
    Intent,
    IntentType,
    MeetingAnalysis,
    Transcript,
    TranscriptSegment,
)
from mainframe.router.models import RouteRule, RouteTarget


# ---------------------------------------------------------------------------
# Transcript fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_segments() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(speaker="Alice", text="Let's decide to launch next week.", start_time=0.0, end_time=3.0),
        TranscriptSegment(speaker="Bob", text="I'll prepare the documentation by Friday.", start_time=3.0, end_time=6.0),
        TranscriptSegment(speaker="Carol", text="What about the testing timeline?", start_time=6.0, end_time=9.0),
        TranscriptSegment(speaker="Dave", text="I commit to finishing QA by Monday.", start_time=9.0, end_time=12.0),
        TranscriptSegment(speaker="Alice", text="Great, the budget is 50k.", start_time=12.0, end_time=15.0),
    ]


@pytest.fixture
def sample_transcript(sample_segments) -> Transcript:
    return Transcript(segments=sample_segments, language="en", duration=15.0)


@pytest.fixture
def sample_transcript_text() -> str:
    return (
        "Alice: Let's decide to launch next week.\n"
        "Bob: I'll prepare the documentation by Friday.\n"
        "Carol: What about the testing timeline?\n"
        "Dave: I commit to finishing QA by Monday.\n"
        "Alice: Great, the budget is 50k.\n"
    )


# ---------------------------------------------------------------------------
# LLM response fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_llm_response() -> dict:
    """A well-formed LLM JSON response matching our schema."""
    return {
        "intents": [
            {
                "type": "decision",
                "content": "Launch next week",
                "confidence": 0.95,
                "speaker": "Alice",
                "timestamp": 1.5,
                "entities": [{"type": "date", "value": "next week"}],
            },
            {
                "type": "action_item",
                "content": "Prepare documentation by Friday",
                "confidence": 0.9,
                "speaker": "Bob",
                "timestamp": 4.5,
                "entities": [{"type": "date", "value": "Friday"}],
            },
            {
                "type": "open_question",
                "content": "What about the testing timeline?",
                "confidence": 0.85,
                "speaker": "Carol",
                "timestamp": 7.5,
                "entities": [],
            },
            {
                "type": "commitment",
                "content": "Finishing QA by Monday",
                "confidence": 0.9,
                "speaker": "Dave",
                "timestamp": 10.5,
                "entities": [{"type": "date", "value": "Monday"}],
            },
            {
                "type": "info",
                "content": "Budget is 50k",
                "confidence": 0.8,
                "speaker": "Alice",
                "timestamp": 13.5,
                "entities": [{"type": "number", "value": "50k"}],
            },
        ],
        "summary": "Team discussed launch timeline. Decided to launch next week. Bob will prepare docs, Dave will finish QA.",
        "decisions": ["Launch next week"],
        "action_items": [{"who": "Bob", "what": "Prepare documentation", "when": "Friday"}],
        "open_questions": ["What about the testing timeline?"],
        "commitments": ["Finishing QA by Monday"],
    }


# ---------------------------------------------------------------------------
# MeetingAnalysis fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_analysis() -> MeetingAnalysis:
    return MeetingAnalysis(
        meeting_id="meeting-test-001",
        summary="Test meeting about launch.",
        intents=[
            Intent(id="intent-1", type=IntentType.DECISION, content="Launch next week", confidence=0.95, speaker="Alice", timestamp=1.5),
            Intent(id="intent-2", type=IntentType.ACTION_ITEM, content="Prepare docs", confidence=0.9, speaker="Bob", timestamp=4.5),
            Intent(id="intent-3", type=IntentType.OPEN_QUESTION, content="Testing timeline?", confidence=0.85, speaker="Carol", timestamp=7.5),
            Intent(id="intent-4", type=IntentType.COMMITMENT, content="QA by Monday", confidence=0.9, speaker="Dave", timestamp=10.5),
            Intent(id="intent-5", type=IntentType.INFO, content="Budget is 50k", confidence=0.8, speaker="Alice", timestamp=13.5),
        ],
        decisions=["Launch next week"],
        action_items=[ActionItem(who="Bob", what="Prepare docs", when="Friday")],
        open_questions=["Testing timeline?"],
        commitments=["QA by Monday"],
    )


# ---------------------------------------------------------------------------
# Routing fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def custom_rules() -> list[RouteRule]:
    """Minimal custom rule set for testing."""
    return [
        RouteRule(id="r1", intent_type="decision", target=RouteTarget.IM_MESSAGE, priority=10),
        RouteRule(id="r2", intent_type="action_item", target=RouteTarget.TASK_TRACKER, priority=10),
    ]
