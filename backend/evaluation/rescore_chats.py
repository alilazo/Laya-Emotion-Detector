"""Recalculate live emotion histories with the current prompt and keep prior snapshots."""

import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.context import build_emotion_context
from app.db import Database
from app.gauge import EMOTIONS, update_gauges
from app.model import EmotionModel
from app.prompts import EMOTION_PROMPT_VERSION


def rescore_live_chats(db: Database, model: EmotionModel, settings: Settings) -> int:
    """Compute all replacements first; one transaction installs them or none."""
    candidates = []
    with db.connection() as conn:
        chats = conn.execute("SELECT * FROM chats WHERE source='live' AND emotion_message_count>0").fetchall()
        for chat in chats:
            old = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM emotion_snapshots WHERE chat_id=? ORDER BY sequence_number", (chat["id"],)
                )
            ]
            if not old or all(item["emotion_prompt_version"] == EMOTION_PROMPT_VERSION for item in old):
                continue
            messages = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM messages WHERE chat_id=? ORDER BY sequence_number", (chat["id"],)
                )
            ]
            candidates.append((dict(chat), old, messages))
    if not candidates:
        return 0

    prepared = []
    for chat, old, messages in candidates:
        old_by_message = {item["message_id"]: item for item in old}
        previous = {key: 0.0 for key in EMOTIONS}
        peak = {key: 0.0 for key in EMOTIONS}
        totals = {key: 0.0 for key in EMOTIONS}
        history = []
        replacements = []
        for message in messages:
            if message["role"] == "user" and message["id"] in old_by_message:
                state = build_emotion_context(message["content"], history[-8:])
                prediction = model.predict(state)
                after = update_gauges(previous, prediction.instant, first=not replacements)
                replacements.append(
                    (
                        str(uuid4()),
                        chat["id"],
                        message["id"],
                        message["sequence_number"],
                        settings.checkpoint,
                        EMOTION_PROMPT_VERSION,
                        *(prediction.raw[key] for key in EMOTIONS),
                        *(prediction.instant[key] for key in EMOTIONS),
                        *(previous[key] for key in EMOTIONS),
                        *(after[key] for key in EMOTIONS),
                        json.dumps(prediction.distributions),
                        message["created_at"],
                    )
                )
                for key in EMOTIONS:
                    peak[key] = max(peak[key], after[key])
                    totals[key] += after[key]
                previous = after
            history.append({"role": message["role"], "content": message["content"]})
        prepared.append((chat, old, replacements, previous, peak, totals))

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = db.path.with_name(f"{db.path.stem}-before-{EMOTION_PROMPT_VERSION}-{stamp}.sqlite3")
    with sqlite3.connect(db.path) as source, sqlite3.connect(backup_path) as backup:
        source.backup(backup)

    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            for chat, old, replacements, previous, peak, totals in prepared:
                current_ids = {
                    row[0] for row in conn.execute("SELECT id FROM emotion_snapshots WHERE chat_id=?", (chat["id"],))
                }
                if current_ids != {item["id"] for item in old}:
                    raise RuntimeError("Chat emotion history changed during rescoring; no replacements were saved")
                for item in old:
                    conn.execute(
                        "INSERT INTO emotion_snapshot_history VALUES(?,?,?,?)",
                        (item["id"], chat["id"], datetime.now(UTC).isoformat(), json.dumps(item)),
                    )
                conn.execute("DELETE FROM emotion_snapshots WHERE chat_id=?", (chat["id"],))
                conn.executemany(
                    "INSERT INTO emotion_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", replacements
                )
                count = len(replacements)
                conn.execute(
                    """UPDATE chats SET current_anxiety=?, current_sadness=?, current_fear=?,
                    peak_anxiety=?, peak_sadness=?, peak_fear=?,
                    average_anxiety=?, average_sadness=?, average_fear=?, emotion_message_count=? WHERE id=?""",
                    (
                        *(previous[key] for key in EMOTIONS),
                        *(peak[key] for key in EMOTIONS),
                        *(totals[key] / count for key in EMOTIONS),
                        count,
                        chat["id"],
                    ),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    print(f"Backup: {backup_path}")
    return len(prepared)


def main() -> None:
    settings = Settings(warmup=False)
    db = Database(settings.database_path)
    db.initialize()
    model = EmotionModel(settings)
    model.load()
    if not model.ready:
        raise RuntimeError(model.error)
    try:
        count = rescore_live_chats(db, model, settings)
        print(f"Rescored {count} live chats.")
    finally:
        model.close()


if __name__ == "__main__":
    main()
