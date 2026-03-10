"""
SQLite-backed persistent store for commitments and entity memory.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from .models import Commitment, CommitmentStatus, EntityFact, EntityMemory

_SCHEMA = """
CREATE TABLE IF NOT EXISTS commitments (
    commitment_id     TEXT PRIMARY KEY,
    content           TEXT NOT NULL,
    owner             TEXT NOT NULL,
    due_date          TEXT,

    source_meeting_id TEXT NOT NULL,
    source_intent_id  TEXT NOT NULL,
    source_text       TEXT NOT NULL,

    status            TEXT NOT NULL DEFAULT 'open',
    first_seen_at     TEXT NOT NULL,
    last_mentioned_at TEXT NOT NULL,
    mention_count     INTEGER DEFAULT 1,
    mention_meetings  TEXT NOT NULL DEFAULT '[]',  -- JSON array

    closed_at         TEXT,
    closed_by         TEXT,
    closed_evidence   TEXT
);

CREATE INDEX IF NOT EXISTS idx_commit_owner  ON commitments(owner);
CREATE INDEX IF NOT EXISTS idx_commit_status ON commitments(status);

CREATE TABLE IF NOT EXISTS entity_facts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type   TEXT NOT NULL,
    entity_value  TEXT NOT NULL,
    meeting_id    TEXT NOT NULL,
    fact          TEXT NOT NULL,
    speaker       TEXT NOT NULL,
    timestamp     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity ON entity_facts(entity_type, entity_value);
"""


class MemoryStore:
    """Async SQLite store for cross-meeting memory."""

    def __init__(self, db_path: str = "mainframe_memory.db") -> None:
        self._db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    # ------------------------------------------------------------------
    # Commitments
    # ------------------------------------------------------------------

    async def save_commitment(self, c: Commitment) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO commitments
               (commitment_id, content, owner, due_date,
                source_meeting_id, source_intent_id, source_text,
                status, first_seen_at, last_mentioned_at,
                mention_count, mention_meetings,
                closed_at, closed_by, closed_evidence)
               VALUES (?, ?, ?, ?,  ?, ?, ?,  ?, ?, ?,  ?, ?,  ?, ?, ?)""",
            (
                c.commitment_id, c.content, c.owner, c.due_date,
                c.source_meeting_id, c.source_intent_id, c.source_text,
                c.status.value, c.first_seen_at.isoformat(), c.last_mentioned_at.isoformat(),
                c.mention_count, json.dumps(c.mention_meetings),
                c.closed_at.isoformat() if c.closed_at else None,
                c.closed_by, c.closed_evidence,
            ),
        )
        await self._db.commit()

    async def get_commitment(self, commitment_id: str) -> Optional[Commitment]:
        cur = await self._db.execute(
            "SELECT * FROM commitments WHERE commitment_id = ?", (commitment_id,)
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return self._row_to_commitment(row, cur.description)

    async def get_open_commitments(self, owner: Optional[str] = None) -> list[Commitment]:
        if owner:
            cur = await self._db.execute(
                "SELECT * FROM commitments WHERE status IN ('open','in_progress','overdue') AND owner = ?",
                (owner,),
            )
        else:
            cur = await self._db.execute(
                "SELECT * FROM commitments WHERE status IN ('open','in_progress','overdue')"
            )
        rows = await cur.fetchall()
        return [self._row_to_commitment(r, cur.description) for r in rows]

    async def get_repeated_commitments(self, min_mentions: int = 2) -> list[Commitment]:
        cur = await self._db.execute(
            "SELECT * FROM commitments WHERE mention_count >= ? ORDER BY mention_count DESC",
            (min_mentions,),
        )
        rows = await cur.fetchall()
        return [self._row_to_commitment(r, cur.description) for r in rows]

    async def update_commitment_status(
        self, commitment_id: str, status: CommitmentStatus, **kwargs
    ) -> Optional[Commitment]:
        sets = ["status = ?"]
        params: list = [status.value]
        for col in ("closed_at", "closed_by", "closed_evidence"):
            if col in kwargs:
                val = kwargs[col]
                if isinstance(val, datetime):
                    val = val.isoformat()
                sets.append(f"{col} = ?")
                params.append(val)
        params.append(commitment_id)
        await self._db.execute(
            f"UPDATE commitments SET {', '.join(sets)} WHERE commitment_id = ?", params
        )
        await self._db.commit()
        return await self.get_commitment(commitment_id)

    async def record_mention(
        self, commitment_id: str, meeting_id: str
    ) -> Optional[Commitment]:
        """Record that a commitment was mentioned again in a new meeting."""
        c = await self.get_commitment(commitment_id)
        if c is None:
            return None
        c.mention_count += 1
        c.last_mentioned_at = datetime.now(timezone.utc)
        if meeting_id not in c.mention_meetings:
            c.mention_meetings.append(meeting_id)
        await self.save_commitment(c)
        return c

    # ------------------------------------------------------------------
    # Entity memory
    # ------------------------------------------------------------------

    async def add_entity_fact(
        self,
        entity_type: str,
        entity_value: str,
        meeting_id: str,
        fact: str,
        speaker: str,
    ) -> None:
        await self._db.execute(
            """INSERT INTO entity_facts (entity_type, entity_value, meeting_id, fact, speaker, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (entity_type, entity_value, meeting_id, fact, speaker,
             datetime.now(timezone.utc).isoformat()),
        )
        await self._db.commit()

    async def get_entity_memory(
        self, entity_type: str, entity_value: str
    ) -> Optional[EntityMemory]:
        cur = await self._db.execute(
            "SELECT * FROM entity_facts WHERE entity_type = ? AND entity_value = ? ORDER BY timestamp",
            (entity_type, entity_value),
        )
        rows = await cur.fetchall()
        if not rows:
            return None

        facts = []
        for row in rows:
            d = self._row_dict(row, cur.description)
            facts.append(EntityFact(
                meeting_id=d["meeting_id"],
                fact=d["fact"],
                speaker=d["speaker"],
                timestamp=datetime.fromisoformat(d["timestamp"]),
            ))

        return EntityMemory(
            entity_type=entity_type,
            entity_value=entity_value,
            facts=facts,
            first_seen_at=facts[0].timestamp,
            last_updated_at=facts[-1].timestamp,
        )

    async def search_entities(self, query: str) -> list[dict]:
        """Search entity facts by keyword."""
        cur = await self._db.execute(
            "SELECT DISTINCT entity_type, entity_value FROM entity_facts WHERE entity_value LIKE ? OR fact LIKE ?",
            (f"%{query}%", f"%{query}%"),
        )
        rows = await cur.fetchall()
        return [{"entity_type": r[0], "entity_value": r[1]} for r in rows]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_dict(row, description) -> dict:
        return {col[0]: row[i] for i, col in enumerate(description)}

    @classmethod
    def _row_to_commitment(cls, row, description) -> Commitment:
        d = cls._row_dict(row, description)
        return Commitment(
            commitment_id=d["commitment_id"],
            content=d["content"],
            owner=d["owner"],
            due_date=d["due_date"],
            source_meeting_id=d["source_meeting_id"],
            source_intent_id=d["source_intent_id"],
            source_text=d["source_text"],
            status=CommitmentStatus(d["status"]),
            first_seen_at=datetime.fromisoformat(d["first_seen_at"]),
            last_mentioned_at=datetime.fromisoformat(d["last_mentioned_at"]),
            mention_count=d["mention_count"],
            mention_meetings=json.loads(d["mention_meetings"]) if d["mention_meetings"] else [],
            closed_at=datetime.fromisoformat(d["closed_at"]) if d["closed_at"] else None,
            closed_by=d["closed_by"],
            closed_evidence=d["closed_evidence"],
        )
