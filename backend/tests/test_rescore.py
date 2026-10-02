import json

from app.config import Settings
from app.db import Database
from app.model import EmotionPrediction
from app.prompts import EMOTION_PROMPT_VERSION
from evaluation.rescore_chats import rescore_live_chats


class CorrectedModel:
    def predict(self, state):
        assert state["current_user_message"] == "I miss my dog."
        raw = {"anxiety": 2.8, "sadness": 3.0, "fear": 2.1}
        instant = {"anxiety": 0, "sadness": 62.5, "fear": 0}
        return EmotionPrediction(raw, instant, {"evidence": {"version": "evidence-v1"}}, 1)


def test_rescore_archives_old_snapshot_and_replaces_live_gauges(tmp_path):
    settings = Settings(database_path=tmp_path / "rescore.sqlite3")
    db = Database(settings.database_path)
    db.initialize()
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO chats(id,title,source,created_at,updated_at,current_anxiety,current_sadness,current_fear,emotion_message_count) VALUES(?,?,?,?,?,?,?,?,?)",
            ("live", "Dog", "live", "2026-09-28", "2026-09-28", 70, 75, 53, 1),
        )
        conn.execute(
            "INSERT INTO messages(id,chat_id,sequence_number,role,content,emotion_status,created_at) VALUES(?,?,?,?,?,?,?)",
            ("message", "live", 1, "user", "I miss my dog.", "ready", "2026-09-28"),
        )
        conn.execute(
            "INSERT INTO emotion_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "old-snapshot",
                "live",
                "message",
                1,
                "typed-decisions",
                "emotion-v1",
                2.8,
                3,
                2.1,
                70,
                75,
                53,
                0,
                0,
                0,
                70,
                75,
                53,
                json.dumps({}),
                "2026-09-28",
            ),
        )
    assert rescore_live_chats(db, CorrectedModel(), settings) == 1
    with db.connection() as conn:
        snapshot = conn.execute("SELECT * FROM emotion_snapshots WHERE chat_id='live'").fetchone()
        archived = conn.execute("SELECT snapshot_json FROM emotion_snapshot_history WHERE chat_id='live'").fetchone()
        chat = conn.execute("SELECT * FROM chats WHERE id='live'").fetchone()
    assert snapshot["emotion_prompt_version"] == EMOTION_PROMPT_VERSION
    assert (snapshot["anxiety_gauge_after"], snapshot["sadness_gauge_after"], snapshot["fear_gauge_after"]) == (
        0,
        62.5,
        0,
    )
    assert json.loads(archived["snapshot_json"])["id"] == "old-snapshot"
    assert (chat["current_anxiety"], chat["current_sadness"], chat["current_fear"]) == (0, 62.5, 0)
    assert rescore_live_chats(db, CorrectedModel(), settings) == 0
