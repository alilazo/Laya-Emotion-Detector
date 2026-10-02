import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'live',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    current_anxiety REAL NOT NULL DEFAULT 0,
    current_sadness REAL NOT NULL DEFAULT 0,
    current_fear REAL NOT NULL DEFAULT 0,
    peak_anxiety REAL NOT NULL DEFAULT 0,
    peak_sadness REAL NOT NULL DEFAULT 0,
    peak_fear REAL NOT NULL DEFAULT 0,
    average_anxiety REAL NOT NULL DEFAULT 0,
    average_sadness REAL NOT NULL DEFAULT 0,
    average_fear REAL NOT NULL DEFAULT 0,
    emotion_message_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content TEXT NOT NULL,
    emotion_status TEXT NOT NULL CHECK(emotion_status IN ('not_applicable','pending','ready','unavailable')),
    created_at TEXT NOT NULL,
    UNIQUE(chat_id, sequence_number)
);
CREATE TABLE IF NOT EXISTS emotion_snapshots (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    message_id TEXT NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    model_checkpoint TEXT NOT NULL,
    emotion_prompt_version TEXT NOT NULL,
    anxiety_raw_score REAL NOT NULL,
    sadness_raw_score REAL NOT NULL,
    fear_raw_score REAL NOT NULL,
    anxiety_instant REAL NOT NULL,
    sadness_instant REAL NOT NULL,
    fear_instant REAL NOT NULL,
    anxiety_gauge_before REAL NOT NULL,
    sadness_gauge_before REAL NOT NULL,
    fear_gauge_before REAL NOT NULL,
    anxiety_gauge_after REAL NOT NULL,
    sadness_gauge_after REAL NOT NULL,
    fear_gauge_after REAL NOT NULL,
    distributions_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(chat_id, sequence_number)
);
CREATE INDEX IF NOT EXISTS ix_messages_chat_order ON messages(chat_id, sequence_number);
CREATE INDEX IF NOT EXISTS ix_snapshots_chat_order ON emotion_snapshots(chat_id, sequence_number);
CREATE INDEX IF NOT EXISTS ix_chats_created ON chats(created_at);
"""

SNAPSHOT_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS emotion_snapshot_history (
    original_snapshot_id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    archived_at TEXT NOT NULL,
    snapshot_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_snapshot_history_chat ON emotion_snapshot_history(chat_id);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > 3:
                raise RuntimeError(f"Unsupported database version: {version}")
            if version == 0:
                conn.executescript(SCHEMA)
            if version <= 1:
                conn.executescript(SNAPSHOT_HISTORY_SCHEMA)
                conn.execute("PRAGMA user_version = 2")
            if version < 3:
                conn.executescript("""
                    BEGIN IMMEDIATE;
                    ALTER TABLE messages ADD COLUMN reasoning TEXT;
                    ALTER TABLE messages ADD COLUMN thinking_ms REAL;
                    ALTER TABLE messages ADD COLUMN response_ms REAL;
                    PRAGMA user_version = 3;
                    COMMIT;
                """)
            # A process interrupted during inference has no trustworthy score.
            conn.execute("UPDATE messages SET emotion_status='unavailable' WHERE emotion_status='pending'")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        try:
            yield conn
        finally:
            conn.close()


def row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def parse_snapshot(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["distributions"] = json.loads(item.pop("distributions_json")) if item["distributions_json"] else None
    return item
