import asyncio

from app.config import Settings
from app.db import Database
from app.main import create_app
from app.model import EmotionPrediction
from app.reply import ChatReply
from app.service import EmotionService
from fastapi.testclient import TestClient


class FakeModel:
    ready = True
    error = None

    def __init__(self):
        self.calls = []
        self.fail = False

    def load(self):
        pass

    def predict(self, state):
        self.calls.append(state)
        if self.fail:
            raise RuntimeError("model unavailable")
        score = 3 if "worried" in state["current_user_message"] else 0
        raw = {"anxiety": score, "sadness": 0, "fear": 0}
        return EmotionPrediction(raw, {key: value * 25 for key, value in raw.items()}, {}, 1)


class FakeChatModel:
    def __init__(self):
        self.calls = []
        self.fail = False
        self.reasoning = None

    async def reply(self, history):
        self.calls.append(history)
        if self.fail:
            raise RuntimeError("Ollama unavailable")
        return ChatReply(f"Reply to: {history[-1]['content']}", self.reasoning, 1250 if self.reasoning else None, 2100)

    async def status(self):
        return "unavailable" if self.fail else "ready"

    async def close(self):
        pass


def test_chat_snapshots_analytics_and_failure(tmp_path):
    fake = FakeModel()
    fake_chat = FakeChatModel()
    app = create_app(
        Settings(database_path=tmp_path / "test.sqlite3", access_token="test-token", laya_enabled=False),
        fake,
        fake_chat,
    )
    headers = {"Authorization": "Bearer test-token"}
    with TestClient(app) as client:
        assert client.get("/api/chats").status_code == 401
        created = client.post("/api/chats", headers=headers, json={}).json()
        chat_id = created["id"]
        assert created["current_anxiety"] == 0
        first = client.post(f"/api/chats/{chat_id}/messages", headers=headers, json={"content": "I am worried."})
        assert first.status_code == 200, first.text
        assert first.json()["emotionStatus"] == "ready"
        assert first.json()["replyStatus"] == "ready"
        assert first.json()["chat"]["messages"][-1]["content"] == "Reply to: I am worried."
        assert fake_chat.calls[0] == [{"role": "user", "content": "I am worried."}]
        assert first.json()["chat"]["current_anxiety"] == 75
        assert len(fake.calls) == 1
        assert fake.calls[0]["evaluation_scope"] == "CURRENT_USER_MESSAGE"
        assert fake.calls[0]["recent_context"] == []
        second = client.post(f"/api/chats/{chat_id}/messages", headers=headers, json={"content": "I feel okay."})
        assert second.status_code == 200, second.text
        assert second.json()["chat"]["current_anxiety"] == 66
        assert len(fake.calls) == 2  # Assistant messages were not scored.
        assert [item["role"] for item in fake_chat.calls[1]] == ["user", "assistant", "user"]
        detail = client.get(f"/api/chats/{chat_id}/emotion", headers=headers).json()
        assert len(detail["timeline"]) == 2
        assert detail["summary"]["peak"]["anxiety"] == 75
        assert detail["summary"]["average"]["anxiety"] == 70.5
        analytics = client.get("/api/emotion/analytics?mode=peak&min_anxiety=70", headers=headers).json()
        assert analytics["summary"]["chatCount"] == 1
        assert len(analytics["chats"]) == 1
        assert analytics["chats"][0]["values"]["anxiety"] == 75
        fake.fail = True
        failed = client.post(
            f"/api/chats/{chat_id}/messages", headers=headers, json={"content": "Another message"}
        ).json()
        assert failed["emotionStatus"] == "unavailable"
        assert failed["chat"]["current_anxiety"] == 66
        assert len(client.get(f"/api/chats/{chat_id}/emotion", headers=headers).json()["timeline"]) == 2
        new_chat = client.post("/api/chats", headers=headers, json={}).json()
        assert new_chat["current_anxiety"] == 0
        assert client.get("/api/emotion/analytics", headers=headers).json()["summary"]["chatCount"] == 1


def test_unanalyzed_chat_and_access(tmp_path):
    app = create_app(
        Settings(database_path=tmp_path / "test.sqlite3", access_token="test-token", laya_enabled=False),
        FakeModel(),
        FakeChatModel(),
    )
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer test-token"}
        chat = client.post("/api/chats", headers=headers, json={}).json()
        assert client.get(f"/api/chats/{chat['id']}/emotion").status_code == 401
        assert client.get(f"/api/chats/{chat['id']}/emotion", headers=headers).json()["summary"] is None
        assert client.get("/api/emotion/analytics", headers=headers).json()["summary"]["chatCount"] == 0


def test_concurrent_messages_apply_in_submission_order(tmp_path):
    settings = Settings(database_path=tmp_path / "ordered.sqlite3", access_token="test-token", laya_enabled=False)
    db = Database(settings.database_path)
    db.initialize()
    service = EmotionService(db, FakeModel(), settings, FakeChatModel())
    chat = service.create_chat()

    async def send_both():
        return await asyncio.gather(
            service.add_user_message(chat["id"], "I am worried."),
            service.add_user_message(chat["id"], "I feel okay."),
        )

    asyncio.run(send_both())
    timeline = service.chat_emotion(chat["id"])["timeline"]
    assert [point["gauge"]["anxiety"] for point in timeline] == [75, 66]
    assert [point["sequence"] for point in timeline] == [1, 2]


def test_interrupted_inference_is_unavailable_on_restart(tmp_path):
    db = Database(tmp_path / "restart.sqlite3")
    db.initialize()
    service = EmotionService(db, FakeModel(), Settings(database_path=db.path, laya_enabled=False), FakeChatModel())
    chat = service.create_chat()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO messages(id,chat_id,sequence_number,role,content,emotion_status,created_at) VALUES(?,?,?,?,?,?,?)",
            ("interrupted", chat["id"], 1, "user", "Message before interruption", "pending", chat["created_at"]),
        )
    db.initialize()
    assert service.get_chat(chat["id"])["messages"][0]["emotion_status"] == "unavailable"
    assert service.chat_emotion(chat["id"])["timeline"] == []


def test_ollama_failure_keeps_user_message_and_emotion_snapshot(tmp_path):
    fake_chat = FakeChatModel()
    fake_chat.fail = True
    app = create_app(
        Settings(database_path=tmp_path / "failed-chat.sqlite3", access_token="test-token", laya_enabled=False),
        FakeModel(),
        fake_chat,
    )
    headers = {"Authorization": "Bearer test-token"}
    with TestClient(app) as client:
        chat_id = client.post("/api/chats", headers=headers, json={}).json()["id"]
        response = client.post(f"/api/chats/{chat_id}/messages", headers=headers, json={"content": "I am worried."})
        assert response.status_code == 200
        result = response.json()
        assert result["replyStatus"] == "unavailable"
        assert "saved" in result["replyError"].lower()
        assert len(result["chat"]["messages"]) == 1
        assert result["chat"]["messages"][0]["role"] == "user"
        assert result["chat"]["current_anxiety"] == 75
        assert len(client.get(f"/api/chats/{chat_id}/emotion", headers=headers).json()["timeline"]) == 1


def test_reasoning_and_timing_persist_and_legacy_replies_are_presented_without_tags(tmp_path):
    settings = Settings(database_path=tmp_path / "reasoning.sqlite3", laya_enabled=False)
    db = Database(settings.database_path)
    db.initialize()
    fake_chat = FakeChatModel()
    fake_chat.reasoning = "Model-supplied thinking."
    service = EmotionService(db, FakeModel(), settings, fake_chat)
    chat = service.create_chat()
    asyncio.run(service.add_user_message(chat["id"], "Hello"))
    reply = service.get_chat(chat["id"])["messages"][-1]
    assert reply["reasoning"] == "Model-supplied thinking."
    assert reply["thinking_ms"] == 1250
    assert reply["response_ms"] == 2100
    with db.connection() as conn:
        conn.execute(
            "UPDATE messages SET content=?,reasoning=NULL,thinking_ms=NULL WHERE id=?",
            ("<think>Older thinking.</think>Older final answer.", reply["id"]),
        )
    db.initialize()
    legacy = service.get_chat(chat["id"])["messages"][-1]
    assert legacy["content"] == "Older final answer."
    assert legacy["reasoning"] == "Older thinking."
    assert legacy["thinking_ms"] is None


def test_delete_is_authorized_and_cascades_all_chat_data(tmp_path):
    settings = Settings(database_path=tmp_path / "delete.sqlite3", access_token="test-token", laya_enabled=False)
    app = create_app(settings, FakeModel(), FakeChatModel())
    headers = {"Authorization": "Bearer test-token"}
    with TestClient(app) as client:
        chat_id = client.post("/api/chats", headers=headers, json={}).json()["id"]
        other_id = client.post("/api/chats", headers=headers, json={}).json()["id"]
        client.post(f"/api/chats/{chat_id}/messages", headers=headers, json={"content": "I am worried."})
        db = Database(settings.database_path)
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO emotion_snapshot_history VALUES (?,?,?,?)",
                ("archived", chat_id, "2026-10-01", "{}"),
            )
        assert client.delete(f"/api/chats/{chat_id}").status_code == 401
        assert client.get(f"/api/chats/{chat_id}", headers=headers).status_code == 200
        assert client.delete(f"/api/chats/{chat_id}", headers=headers).json() == {"deleted": True}
        assert client.get(f"/api/chats/{chat_id}", headers=headers).status_code == 404
        assert client.get(f"/api/chats/{chat_id}/emotion", headers=headers).status_code == 404
        assert client.delete(f"/api/chats/{chat_id}", headers=headers).status_code == 404
        assert client.get(f"/api/chats/{other_id}", headers=headers).status_code == 200
        assert client.get("/api/emotion/analytics", headers=headers).json()["summary"]["chatCount"] == 0
        with db.connection() as conn:
            for table in ("messages", "emotion_snapshots", "emotion_snapshot_history"):
                assert conn.execute(f"SELECT COUNT(*) FROM {table} WHERE chat_id=?", (chat_id,)).fetchone()[0] == 0
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_delete_waits_for_an_in_flight_reply(tmp_path):
    settings = Settings(database_path=tmp_path / "delete-in-flight.sqlite3", laya_enabled=False)
    db = Database(settings.database_path)
    db.initialize()

    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()

        class WaitingChatModel(FakeChatModel):
            async def reply(self, history):
                entered.set()
                await release.wait()
                return await super().reply(history)

        service = EmotionService(db, FakeModel(), settings, WaitingChatModel())
        chat_id = service.create_chat()["id"]
        send = asyncio.create_task(service.add_user_message(chat_id, "Hello"))
        await entered.wait()
        deletion = asyncio.create_task(service.delete_chat(chat_id))
        await asyncio.sleep(0)
        assert not deletion.done()
        release.set()
        assert (await send)["replyStatus"] == "ready"
        assert await deletion is True
        assert service.get_chat(chat_id) is None
        assert await service.add_user_message(chat_id, "After deletion") is None

    asyncio.run(exercise())
