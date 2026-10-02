"""Live-model regression checks for unsupported cross-emotion scores."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.context import build_emotion_context
from app.model import EmotionModel


def main():
    model = EmotionModel(Settings(warmup=False))
    model.load()
    if not model.ready:
        raise RuntimeError(model.error)
    failures = []
    for text, bounds in [
        ("I really miss my dog today.", {"anxiety": (0, 25), "sadness": (25, 100), "fear": (0, 25)}),
        ("The weather is nice today.", {"anxiety": (0, 25), "sadness": (0, 25), "fear": (0, 25)}),
        ("I'm not scared anymore.", {"anxiety": (0, 25), "sadness": (0, 25), "fear": (0, 25)}),
        ("Okay but I am also really scared for her", {"fear": (50, 100)}),
    ]:
        scores = model.predict(build_emotion_context(text, [])).instant
        print(text, {key: round(value, 1) for key, value in scores.items()}, flush=True)
        for key, (low, high) in bounds.items():
            if not low <= scores[key] <= high:
                failures.append(f"{text}: {key}={scores[key]:.1f}, expected {low}..{high}")
    assert not failures, "\n".join(failures)
    print("Scoring regression checks passed.")


if __name__ == "__main__":
    main()
