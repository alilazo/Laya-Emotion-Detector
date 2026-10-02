import asyncio
import json
import logging
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from .analytics import metrics, values_for_mode
from .chat_model import ChatModelError, OllamaChatModel
from .config import Settings
from .context import build_emotion_context
from .db import Database, parse_snapshot, row_dict
from .gauge import EMOTIONS, update_gauges
from .model import EmotionModel
from .prompts import EMOTION_PROMPT_VERSION
from .reply import present_message

LOG = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(UTC).isoformat()


class EmotionService:
    def __init__(self, db: Database, model: EmotionModel, settings: Settings, chat_model: OllamaChatModel):
        self.db, self.model, self.settings, self.chat_model = db, model, settings, chat_model
        self._locks: dict[str, asyncio.Lock] = {}

    def create_chat(self, title: str = "New conversation", source: str = "live") -> dict:
        chat_id, timestamp = str(uuid4()), now()
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO chats(id,title,source,created_at,updated_at) VALUES(?,?,?,?,?)",
                (chat_id, title, source, timestamp, timestamp),
            )
            return row_dict(conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone())

    def list_chats(self) -> list[dict]:
        with self.db.connection() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM chats ORDER BY updated_at DESC")]

    def get_chat(self, chat_id: str) -> dict | None:
        with self.db.connection() as conn:
            chat = row_dict(conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone())
            if not chat:
                return None
            chat["messages"] = [
                present_message(dict(row))
                for row in conn.execute("SELECT * FROM messages WHERE chat_id=? ORDER BY sequence_number", (chat_id,))
            ]
            return chat

    async def delete_chat(self, chat_id: str) -> bool:
        # Wait for any in-flight reply before cascading the conversation's data.
        async with self._locks.setdefault(chat_id, asyncio.Lock()):
            with self.db.connection() as conn:
                return conn.execute("DELETE FROM chats WHERE id=?", (chat_id,)).rowcount > 0

    async def add_user_message(self, chat_id: str, content: str) -> dict | None:
        # Hold the chat lock through inference so snapshots are applied in message order.
        async with self._locks.setdefault(chat_id, asyncio.Lock()):
            with self.db.connection() as conn:
                chat = conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()
                if chat is None:
                    return None
                sequence = conn.execute(
                    "SELECT COALESCE(MAX(sequence_number),0)+1 FROM messages WHERE chat_id=?", (chat_id,)
                ).fetchone()[0]
                message_id, timestamp = str(uuid4()), now()
                conn.execute(
                    "INSERT INTO messages(id,chat_id,sequence_number,role,content,emotion_status,created_at) VALUES(?,?,?,?,?,?,?)",
                    (message_id, chat_id, sequence, "user", content, "pending", timestamp),
                )
                previous = {key: float(chat[f"current_{key}"]) for key in EMOTIONS}
                count = int(chat["emotion_message_count"])
                recent = [
                    dict(row)
                    for row in conn.execute(
                        "SELECT role,content FROM messages WHERE chat_id=? AND sequence_number<? ORDER BY sequence_number DESC LIMIT 8",
                        (chat_id, sequence),
                    )
                ][::-1]

            pipeline_start = perf_counter()
            context_start = perf_counter()
            context = build_emotion_context(content, recent)
            context_ms = (perf_counter() - context_start) * 1000
            try:
                prediction = await asyncio.to_thread(self.model.predict, context)
                before = previous
                after = update_gauges(previous, prediction.instant, first=count == 0)
                gauge_ms = (perf_counter() - pipeline_start) * 1000 - context_ms - prediction.inference_ms
                write_start = perf_counter()
                with self.db.connection() as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    try:
                        conn.execute(
                            """INSERT INTO emotion_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                str(uuid4()),
                                chat_id,
                                message_id,
                                sequence,
                                self.settings.checkpoint,
                                EMOTION_PROMPT_VERSION,
                                *(prediction.raw[key] for key in EMOTIONS),
                                *(prediction.instant[key] for key in EMOTIONS),
                                *(before[key] for key in EMOTIONS),
                                *(after[key] for key in EMOTIONS),
                                json.dumps(prediction.distributions),
                                timestamp,
                            ),
                        )
                        updates = {f"current_{key}": after[key] for key in EMOTIONS}
                        updates.update({f"peak_{key}": max(float(chat[f"peak_{key}"]), after[key]) for key in EMOTIONS})
                        updates.update(
                            {
                                f"average_{key}": (float(chat[f"average_{key}"]) * count + after[key]) / (count + 1)
                                for key in EMOTIONS
                            }
                        )
                        assignments = ", ".join(f"{key}=?" for key in updates)
                        conn.execute(
                            f"UPDATE chats SET {assignments}, emotion_message_count=?, updated_at=? WHERE id=?",
                            (*updates.values(), count + 1, timestamp, chat_id),
                        )
                        conn.execute("UPDATE messages SET emotion_status='ready' WHERE id=?", (message_id,))
                        conn.execute("COMMIT")
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise
                db_ms = (perf_counter() - write_start) * 1000
                status = "ready"
                LOG.info(
                    "emotion_scored chat=%s message=%s checkpoint=%s context_ms=%.1f inference_ms=%.1f gauge_ms=%.1f db_ms=%.1f total_ms=%.1f",
                    chat_id,
                    message_id,
                    self.settings.checkpoint,
                    context_ms,
                    prediction.inference_ms,
                    gauge_ms,
                    db_ms,
                    (perf_counter() - pipeline_start) * 1000,
                )
            except Exception as exc:  # noqa: BLE001 - any inference failure must preserve normal chat
                LOG.warning("emotion_unavailable chat=%s message=%s reason=%s", chat_id, message_id, type(exc).__name__)
                with self.db.connection() as conn:
                    conn.execute("UPDATE messages SET emotion_status='unavailable' WHERE id=?", (message_id,))
                status = "unavailable"

            with self.db.connection() as conn:
                recent_chat = [
                    dict(row)
                    for row in conn.execute(
                        "SELECT role,content FROM messages WHERE chat_id=? ORDER BY sequence_number DESC LIMIT 24",
                        (chat_id,),
                    )
                ][::-1]
            reply_start = perf_counter()
            reply_status, reply_error = "ready", None
            try:
                reply = await self.chat_model.reply(recent_chat)
                LOG.info(
                    "chat_replied chat=%s model=%s duration_ms=%.1f",
                    chat_id,
                    self.settings.ollama_model,
                    (perf_counter() - reply_start) * 1000,
                )
            except ChatModelError as exc:
                reply_status, reply_error = "unavailable", str(exc)
                LOG.warning("chat_unavailable chat=%s reason=%s", chat_id, exc)
            except Exception as exc:
                reply_status, reply_error = "unavailable", "Ollama could not generate a reply. Your message was saved."
                LOG.exception("chat_unavailable chat=%s reason=%s", chat_id, type(exc).__name__)

            with self.db.connection() as conn:
                reply_at = now()
                if reply_status == "ready":
                    conn.execute(
                        """INSERT INTO messages(id,chat_id,sequence_number,role,content,emotion_status,created_at,
                        reasoning,thinking_ms,response_ms) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (
                            str(uuid4()),
                            chat_id,
                            sequence + 1,
                            "assistant",
                            reply.content,
                            "not_applicable",
                            reply_at,
                            reply.reasoning,
                            reply.thinking_ms,
                            reply.response_ms,
                        ),
                    )
                conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (reply_at, chat_id))
                if sequence == 1 and chat["title"] == "New conversation":
                    title = " ".join(content.split())[:52] or "New conversation"
                    conn.execute("UPDATE chats SET title=? WHERE id=?", (title, chat_id))
            return {
                "messageId": message_id,
                "emotionStatus": status,
                "replyStatus": reply_status,
                "replyError": reply_error,
                "chat": self.get_chat(chat_id),
            }

    def chat_emotion(self, chat_id: str) -> dict | None:
        with self.db.connection() as conn:
            chat = conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()
            if chat is None:
                return None
            snapshots = [
                parse_snapshot(row)
                for row in conn.execute(
                    "SELECT * FROM emotion_snapshots WHERE chat_id=? ORDER BY sequence_number", (chat_id,)
                )
            ]
        return {
            "summary": {mode: values_for_mode(dict(chat), mode) for mode in ("final", "peak", "average")}
            if snapshots
            else None,
            "timeline": [
                {
                    "sequence": index + 1,
                    "messageId": snap["message_id"],
                    "createdAt": snap["created_at"],
                    "instant": {key: snap[f"{key}_instant"] for key in EMOTIONS},
                    "gauge": {key: snap[f"{key}_gauge_after"] for key in EMOTIONS},
                }
                for index, snap in enumerate(snapshots)
            ],
        }

    def analytics(
        self, mode: str, start_date: str | None, end_date: str | None, min_scores: dict, dominant: str, search: str
    ) -> dict:
        started = perf_counter()
        with self.db.connection() as conn:
            rows = [
                dict(row)
                for row in conn.execute("SELECT * FROM chats WHERE emotion_message_count>0 ORDER BY created_at DESC")
            ]
        dated = [
            row
            for row in rows
            if (not start_date or row["created_at"][:10] >= start_date)
            and (not end_date or row["created_at"][:10] <= end_date)
        ]
        all_nodes = []
        for row in dated:
            item = metrics(values_for_mode(row, mode), self.settings.neutral_threshold, self.settings.mixed_threshold)
            all_nodes.append(
                {
                    "chatId": row["id"],
                    "title": row["title"],
                    "source": row["source"],
                    "createdAt": row["created_at"],
                    "messageCount": row["emotion_message_count"],
                    **item,
                }
            )
        summary = {
            "chatCount": len(all_nodes),
            **{
                f"average{key.title()}": sum(node["values"][key] for node in all_nodes) / len(all_nodes)
                if all_nodes
                else 0
                for key in EMOTIONS
            },
            "highAnxietyChats": sum(node["values"]["anxiety"] >= self.settings.high_threshold for node in all_nodes),
            "highSadnessChats": sum(node["values"]["sadness"] >= self.settings.high_threshold for node in all_nodes),
            "highFearChats": sum(node["values"]["fear"] >= self.settings.high_threshold for node in all_nodes),
            "mixedChats": sum(node["mixed"] for node in all_nodes),
        }
        filtered = [
            node
            for node in all_nodes
            if all(node["values"][key] >= min_scores[key] for key in EMOTIONS)
            and (
                dominant == "all"
                or node["dominantEmotion"] == dominant
                or (dominant == "mixed" and node["mixed"])
                or (dominant == "low" and all(node["values"][key] < 25 for key in EMOTIONS))
            )
            and search.lower() in node["title"].lower()
        ]
        LOG.info("analytics mode=%s duration_ms=%.1f rows=%s", mode, (perf_counter() - started) * 1000, len(filtered))
        return {"summary": summary, "chats": filtered, "totalInDateRange": len(all_nodes)}
