"""Tests for Memory subsystem — models, store, and CommitmentMatcher."""

import pytest
from mainframe.memory.models import Commitment, CommitmentStatus, EntityFact
from mainframe.memory.store import MemoryStore
from mainframe.memory.matcher import CommitmentMatcher
from mainframe.understanding.batch.models import Intent, IntentType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def store(tmp_path):
    s = MemoryStore(str(tmp_path / "mem.db"))
    await s.init()
    yield s
    await s.close()


def _commitment(commitment_id="c1", owner="Alice", content="prepare the docs",
                meeting_id="m1"):
    return Commitment(
        commitment_id=commitment_id,
        content=content,
        owner=owner,
        source_meeting_id=meeting_id,
        source_intent_id="i1",
        source_text=content,
        mention_meetings=[meeting_id],
    )


def _intent(content="prepare the documents", speaker="Alice",
            itype=IntentType.ACTION_ITEM):
    return Intent(
        id="i99", type=itype, content=content,
        speaker=speaker, timestamp=1.0, confidence=0.9,
    )


# ---------------------------------------------------------------------------
# Commitment persistence
# ---------------------------------------------------------------------------

class TestCommitmentStore:
    @pytest.mark.asyncio
    async def test_save_and_get(self, store):
        c = _commitment()
        await store.save_commitment(c)
        found = await store.get_commitment("c1")
        assert found is not None
        assert found.owner == "Alice"
        assert found.status == CommitmentStatus.OPEN

    @pytest.mark.asyncio
    async def test_get_not_found(self, store):
        assert await store.get_commitment("nope") is None

    @pytest.mark.asyncio
    async def test_get_open_commitments(self, store):
        await store.save_commitment(_commitment("c1", owner="Alice"))
        await store.save_commitment(_commitment("c2", owner="Bob"))
        all_open = await store.get_open_commitments()
        assert len(all_open) == 2

    @pytest.mark.asyncio
    async def test_get_open_commitments_by_owner(self, store):
        await store.save_commitment(_commitment("c1", owner="Alice"))
        await store.save_commitment(_commitment("c2", owner="Bob"))
        alice_open = await store.get_open_commitments(owner="Alice")
        assert len(alice_open) == 1
        assert alice_open[0].owner == "Alice"

    @pytest.mark.asyncio
    async def test_update_status_to_completed(self, store):
        await store.save_commitment(_commitment())
        updated = await store.update_commitment_status(
            "c1", CommitmentStatus.COMPLETED,
            closed_by="Alice", closed_evidence="Done in meeting m2",
        )
        assert updated.status == CommitmentStatus.COMPLETED
        assert updated.closed_by == "Alice"

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, store):
        result = await store.update_commitment_status("nope", CommitmentStatus.COMPLETED)
        assert result is None

    @pytest.mark.asyncio
    async def test_record_mention(self, store):
        await store.save_commitment(_commitment())
        updated = await store.record_mention("c1", "m2")
        assert updated.mention_count == 2
        assert "m2" in updated.mention_meetings

    @pytest.mark.asyncio
    async def test_record_mention_deduplicates_meetings(self, store):
        await store.save_commitment(_commitment())
        await store.record_mention("c1", "m1")  # already in list
        found = await store.get_commitment("c1")
        # m1 should not be duplicated
        assert found.mention_meetings.count("m1") == 1

    @pytest.mark.asyncio
    async def test_get_repeated_commitments(self, store):
        c1 = _commitment("c1")
        c1.mention_count = 3
        c2 = _commitment("c2")
        c2.mention_count = 1
        await store.save_commitment(c1)
        await store.save_commitment(c2)
        repeated = await store.get_repeated_commitments(min_mentions=2)
        assert len(repeated) == 1
        assert repeated[0].commitment_id == "c1"

    @pytest.mark.asyncio
    async def test_closed_commitments_not_in_open(self, store):
        c = _commitment()
        c.status = CommitmentStatus.COMPLETED
        await store.save_commitment(c)
        open_list = await store.get_open_commitments()
        assert len(open_list) == 0


# ---------------------------------------------------------------------------
# Entity memory
# ---------------------------------------------------------------------------

class TestEntityMemoryStore:
    @pytest.mark.asyncio
    async def test_add_and_get_fact(self, store):
        await store.add_entity_fact("supplier", "ACME", "m1", "signed contract", "Alice")
        mem = await store.get_entity_memory("supplier", "ACME")
        assert mem is not None
        assert mem.entity_value == "ACME"
        assert len(mem.facts) == 1
        assert mem.facts[0].fact == "signed contract"

    @pytest.mark.asyncio
    async def test_multiple_facts_ordered(self, store):
        await store.add_entity_fact("person", "Bob", "m1", "assigned task", "Alice")
        await store.add_entity_fact("person", "Bob", "m2", "completed task", "Alice")
        mem = await store.get_entity_memory("person", "Bob")
        assert len(mem.facts) == 2
        assert mem.facts[0].fact == "assigned task"

    @pytest.mark.asyncio
    async def test_get_nonexistent_entity(self, store):
        mem = await store.get_entity_memory("planet", "Mars")
        assert mem is None

    @pytest.mark.asyncio
    async def test_search_entities(self, store):
        await store.add_entity_fact("supplier", "ACME Corp", "m1", "key supplier", "Alice")
        await store.add_entity_fact("project", "Orion", "m1", "launch project", "Bob")
        results = await store.search_entities("ACME")
        assert len(results) == 1
        assert results[0]["entity_value"] == "ACME Corp"

    @pytest.mark.asyncio
    async def test_search_by_fact_content(self, store):
        await store.add_entity_fact("customer", "Beta Inc", "m1", "big contract signed", "Alice")
        results = await store.search_entities("contract")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# CommitmentMatcher
# ---------------------------------------------------------------------------

class TestCommitmentMatcher:
    def setup_method(self):
        self.matcher = CommitmentMatcher(overlap_threshold=0.5)

    def _open_commitments(self):
        return [
            _commitment("c1", owner="Alice", content="prepare the docs"),
            _commitment("c2", owner="Bob", content="review the budget"),
        ]

    def test_match_same_owner_high_overlap(self):
        intent = _intent("prepare the documents for launch", speaker="Alice")
        result = self.matcher.match(intent, self._open_commitments())
        assert result is not None
        assert result.commitment_id == "c1"

    def test_no_match_wrong_owner(self):
        intent = _intent("prepare the docs", speaker="Charlie")
        result = self.matcher.match(intent, self._open_commitments())
        assert result is None

    def test_no_match_low_overlap(self):
        intent = _intent("schedule a call with the team", speaker="Alice")
        result = self.matcher.match(intent, self._open_commitments())
        assert result is None

    def test_non_matchable_type_returns_none(self):
        intent = _intent("prepare the docs", speaker="Alice", itype=IntentType.INFO)
        result = self.matcher.match(intent, self._open_commitments())
        assert result is None

    def test_decision_type_returns_none(self):
        intent = _intent("prepare the docs", speaker="Alice", itype=IntentType.DECISION)
        result = self.matcher.match(intent, self._open_commitments())
        assert result is None

    def test_commitment_type_matchable(self):
        intent = _intent("prepare the docs", speaker="Alice", itype=IntentType.COMMITMENT)
        result = self.matcher.match(intent, self._open_commitments())
        assert result is not None

    def test_find_new_commitments_new(self):
        intent = _intent("buy new servers for the team", speaker="Alice")
        assert self.matcher.find_new_commitments(intent, self._open_commitments()) is True

    def test_find_new_commitments_existing(self):
        intent = _intent("prepare the docs report", speaker="Alice")
        assert self.matcher.find_new_commitments(intent, self._open_commitments()) is False

    def test_empty_open_list_is_new(self):
        intent = _intent("do something", speaker="Alice")
        assert self.matcher.find_new_commitments(intent, []) is True

    def test_owner_match_case_insensitive(self):
        intent = _intent("prepare the docs", speaker="alice")
        result = self.matcher.match(intent, self._open_commitments())
        assert result is not None

    # --- P0-2: Anti-match (false positive) regression tests ---

    def test_no_false_positive_different_topic(self):
        """Intent about 'servers' must NOT match commitment about 'docs'."""
        intent = _intent("set up new servers for deployment", speaker="Alice")
        result = self.matcher.match(intent, self._open_commitments())
        assert result is None

    def test_no_false_positive_partial_word_overlap(self):
        """Sharing one content word ('review') is insufficient at 50% threshold."""
        commitments = [_commitment("c1", owner="Alice", content="review quarterly budget report")]
        intent = _intent("review the deployment checklist before launch", speaker="Alice")
        result = self.matcher.match(intent, commitments)
        assert result is None

    def test_no_false_positive_common_verbs_only(self):
        """Two sentences sharing only common verbs should not match."""
        commitments = [_commitment("c1", owner="Alice", content="prepare slides for keynote")]
        intent = _intent("prepare agenda for standup", speaker="Alice")
        result = self.matcher.match(intent, commitments)
        assert result is None

    def test_true_positive_high_overlap(self):
        """Very similar content with same owner should match."""
        commitments = [_commitment("c1", owner="Alice", content="finalize budget report")]
        intent = _intent("finalize the budget report draft", speaker="Alice")
        result = self.matcher.match(intent, commitments)
        assert result is not None
        assert result.commitment_id == "c1"

    def test_threshold_boundary_below(self):
        """Overlap exactly below threshold → no match."""
        # 'prepare' is the only shared token between these (1 / 3 = 0.33 < 0.5)
        commitments = [_commitment("c1", owner="Alice", content="prepare slides keynote")]
        intent = _intent("prepare agenda standup", speaker="Alice")
        result = self.matcher.match(intent, commitments)
        assert result is None
