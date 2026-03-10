"""
Commitment matcher — detects when a new intent matches an existing open commitment.

MVP uses owner + keyword overlap. Phase 3 will use embeddings.
"""

from __future__ import annotations

from typing import Optional

from ..understanding.batch.models import Intent, IntentType
from .models import Commitment


_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "are", "was", "will",
    "have", "has", "had", "but", "not", "from", "all", "can", "been",
    "its", "our", "their", "you", "your", "they", "them", "his", "her",
}


def _tokenize(text: str) -> set[str]:
    """Lowercase split into meaningful word tokens, filtering stopwords and short words."""
    return {
        w for w in text.lower().split()
        if len(w) > 2 and w not in _STOPWORDS
    }


class CommitmentMatcher:
    """
    Matches new intents against open commitments.

    An intent matches if:
    1. Same owner (speaker == commitment.owner), AND
    2. Keyword overlap ≥ threshold (default 30%)

    Only ACTION_ITEM and COMMITMENT intents are considered.
    """

    MATCHABLE_TYPES = {IntentType.ACTION_ITEM, IntentType.COMMITMENT}

    def __init__(self, overlap_threshold: float = 0.5):
        self.overlap_threshold = overlap_threshold

    def match(
        self, intent: Intent, open_commitments: list[Commitment]
    ) -> Optional[Commitment]:
        """
        Find the best matching open commitment for an intent.

        Returns ``None`` if no match above threshold.
        """
        if intent.type not in self.MATCHABLE_TYPES:
            return None

        intent_tokens = _tokenize(intent.content)
        if not intent_tokens:
            return None

        best: Optional[Commitment] = None
        best_score = 0.0

        for commitment in open_commitments:
            if not self._owner_matches(intent.speaker, commitment.owner):
                continue

            commit_tokens = _tokenize(commitment.content)
            if not commit_tokens:
                continue

            overlap = len(intent_tokens & commit_tokens)
            score = overlap / min(len(intent_tokens), len(commit_tokens))

            if score >= self.overlap_threshold and score > best_score:
                best = commitment
                best_score = score

        return best

    def find_new_commitments(
        self, intent: Intent, open_commitments: list[Commitment]
    ) -> bool:
        """Return True if the intent is a new commitment (no match found)."""
        if intent.type not in self.MATCHABLE_TYPES:
            return False
        return self.match(intent, open_commitments) is None

    @staticmethod
    def _owner_matches(speaker: str, owner: str) -> bool:
        """Case-insensitive owner comparison."""
        return speaker.strip().lower() == owner.strip().lower()
