import sqlite3

from app.chat_model import chat_messages
from app.db import SCHEMA, Database
from app.reply import ReplyStream, split_thinking


def test_thinking_blocks_and_incomplete_thinking_do_not_leak_into_answer():
    reply = split_thinking("  <think>First.</think>\n<think>Second.</think>\nFinal answer.")
    assert reply.reasoning == "First.\n\nSecond."
    assert reply.content == "Final answer."
    incomplete = split_thinking("<think>Still working")
    assert incomplete.reasoning == "Still working"
    assert incomplete.content == ""
    assert split_thinking("Use `<think>` in your example.").content == "Use `<think>` in your example."
    assert split_thinking("Plain answer.").reasoning is None


def test_observed_thinking_time_excludes_loading_and_answer_generation():
    stream = ReplyStream()
    stream.add("<thi", "", 10.0)
    stream.add("nk>First thought.", "", 12.0)
    stream.add(" More thinking.</think>", "", 13.0)
    stream.add("Final", "", 14.0)
    stream.add(" answer.", "", 18.0)
    reply = stream.finish(18000)
    assert reply.content == "Final answer."
    assert reply.thinking_ms == 2000
    assert reply.response_ms == 18000


def test_chat_context_excludes_saved_thinking_but_preserves_user_text():
    messages = chat_messages(
        [
            {"role": "assistant", "content": "<think>Private model output.</think>Final answer."},
            {"role": "user", "content": "What does <think> mean?"},
        ]
    )
    assert messages[-2]["content"] == "Final answer."
    assert messages[-1]["content"] == "What does <think> mean?"


def test_v2_database_migration_preserves_existing_messages(tmp_path):
    path = tmp_path / "v2.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute("PRAGMA user_version=2")
        conn.execute("INSERT INTO chats(id,title,created_at,updated_at) VALUES('chat','Title','now','now')")
        conn.execute(
            "INSERT INTO messages VALUES('reply','chat',1,'assistant','<think>Old.</think>Answer.','not_applicable','now')"
        )
    db = Database(path)
    db.initialize()
    db.initialize()
    with db.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
        message = conn.execute("SELECT * FROM messages").fetchone()
        assert message["content"] == "<think>Old.</think>Answer."
        assert message["thinking_ms"] is None
