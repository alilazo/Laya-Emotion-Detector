import json
from pathlib import Path

import pytest
from app.analytics import metrics, values_for_mode
from app.context import build_emotion_context
from app.evidence import quote_in_message
from app.gauge import update_emotion_gauge, update_gauges
from app.model import EmotionScoreCalibrator


def test_gauge_rises_and_decays():
    assert update_emotion_gauge(20, 90) == pytest.approx(69)
    assert update_emotion_gauge(0, 62.5) == 62.5
    assert update_emotion_gauge(69, 5) == pytest.approx(61.32)
    value = 80
    for _ in range(8):
        value = update_emotion_gauge(value, 0)
    assert 0 < value < 80


def test_gauges_start_independent_and_bounded():
    previous = {"anxiety": 10, "sadness": 40, "fear": 20}
    instant = {"anxiety": 90, "sadness": 40, "fear": 20}
    assert update_gauges(previous, instant, True) == instant
    updated = update_gauges(previous, instant, False)
    assert updated["sadness"] == 40 and updated["fear"] == 20
    assert updated["anxiety"] > previous["anxiety"]
    assert update_emotion_gauge(-50, 200) == 100


def test_evidence_calibration_blocks_unsupported_emotions():
    calibrator = EmotionScoreCalibrator()
    assert calibrator.calibrate("anxiety", 2.8, 0) == 0
    assert calibrator.calibrate("sadness", 3.5, 2) == 2.5
    assert calibrator.calibrate("fear", 2.8, 3) == 2.8
    assert quote_in_message(
        "I can't stop crying about what happened...", "I can't stop crying about what happened and I'm scared"
    )
    assert not quote_in_message("I am frightened", "My sister is frightened, but I am fine")


def test_context_prioritizes_current_message_and_roles():
    long_text = "beginning " + "middle " * 1500 + "ending fear"
    context = [{"role": "assistant", "content": "Are you scared?"}] * 20
    result = build_emotion_context(long_text, context, budget=300)
    assert result["evaluation_scope"] == "CURRENT_USER_MESSAGE"
    assert result["current_user_message"].startswith("beginning")
    assert result["current_user_message"].endswith("ending fear")
    assert len(result["recent_context"]) < len(context)


def test_constellation_math_and_modes():
    for emotion in ("anxiety", "sadness", "fear"):
        values = {key: 100 if key == emotion else 0 for key in ("anxiety", "sadness", "fear")}
        result = metrics(values)
        assert result["position"][emotion] == 1
        assert result["dominantEmotion"] == emotion
    center = metrics({"anxiety": 50, "sadness": 50, "fear": 50})
    assert all(weight == pytest.approx(1 / 3) for weight in center["position"].values())
    assert center["overallIntensity"] == pytest.approx(50)
    assert not center["mixed"]
    neutral = metrics({"anxiety": 0, "sadness": 0, "fear": 0})
    assert neutral["dominantEmotion"] == "neutral"
    assert all(weight == pytest.approx(1 / 3) for weight in neutral["position"].values())
    assert metrics({"anxiety": 80, "sadness": 20, "fear": 75})["mixed"]
    chat = {
        f"{prefix}_{emotion}": value
        for prefix, value in (("current", 10), ("peak", 70), ("average", 42))
        for emotion in ("anxiety", "sadness", "fear")
    }
    assert values_for_mode(chat, "final")["anxiety"] == 10
    assert values_for_mode(chat, "peak")["fear"] == 70
    assert values_for_mode(chat, "average")["sadness"] == 42


def test_seed_dataset_has_required_coverage():
    cases = json.loads(
        (Path(__file__).resolve().parents[1] / "evaluation" / "emotion_cases.json").read_text(encoding="utf-8")
    )
    assert 40 <= len(cases) <= 60
    assert any(case.get("context") for case in cases)
    assert any(all(value == 0 for value in case["expected"].values()) for case in cases)
    assert any(all(value >= 3 for value in case["expected"].values()) for case in cases)
    assert all(set(case["expected"]) == {"anxiety", "sadness", "fear"} for case in cases)
