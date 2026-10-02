"""Compare Laya checkpoints against illustrative, non-clinical ordinal labels."""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.context import build_emotion_context
from app.gauge import EMOTIONS
from app.model import EmotionModel


def rank(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    result = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][0] == ordered[start][0]:
            end += 1
        average_rank = (start + end - 1) / 2
        for _, index in ordered[start:end]:
            result[index] = average_rank
        start = end
    return result


def spearman(actual: list[float], predicted: list[float]) -> float | None:
    if len(actual) < 2:
        return None
    a, p = rank(actual), rank(predicted)
    am, pm = mean(a), mean(p)
    numerator = sum((x - am) * (y - pm) for x, y in zip(a, p))
    denominator = (sum((x - am) ** 2 for x in a) * sum((y - pm) ** 2 for y in p)) ** 0.5
    return numerator / denominator if denominator else None


def evaluate(checkpoint: str, cases: list[dict], device: str) -> dict:
    settings = Settings(checkpoint=checkpoint, device=device, warmup=False)
    model = EmotionModel(settings)
    model.load()
    if not model.ready:
        raise RuntimeError(f"{checkpoint} failed to load: {model.error}")
    actual = {key: [] for key in EMOTIONS}
    predicted = {key: [] for key in EMOTIONS}
    raw_predicted = {key: [] for key in EMOTIONS}
    confusion = {key: [[0 for _ in range(5)] for _ in range(5)] for key in EMOTIONS}
    neutral_false_positives = 0
    neutral_count = 0
    for case in cases:
        state = build_emotion_context(case["text"], case.get("context", []))
        result = model.predict(state)
        expected_neutral = all(case["expected"][key] == 0 for key in EMOTIONS)
        if expected_neutral:
            neutral_count += 1
            neutral_false_positives += any(result.instant[key] >= 25 for key in EMOTIONS)
        for key in EMOTIONS:
            expected = case["expected"][key]
            score = result.instant[key] / 25
            actual[key].append(expected)
            predicted[key].append(score)
            raw_predicted[key].append(result.raw[key])
            confusion[key][expected][min(4, round(score))] += 1
    maes = {key: mean(abs(a - p) for a, p in zip(actual[key], predicted[key])) for key in EMOTIONS}
    return {
        "checkpoint": checkpoint,
        "cases": len(cases),
        "mae": maes,
        "macro_mae": mean(maes.values()),
        "raw_macro_mae": mean(mean(abs(a - p) for a, p in zip(actual[key], raw_predicted[key])) for key in EMOTIONS),
        "spearman": {key: spearman(actual[key], predicted[key]) for key in EMOTIONS},
        "neutral_false_positive_rate": neutral_false_positives / neutral_count if neutral_count else None,
        "rounded_confusion": confusion,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name("emotion_cases.json"))
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps", "xpu"], default="auto")
    parser.add_argument("--checkpoint", choices=["both", "english", "typed-decisions"], default="both")
    args = parser.parse_args()
    cases = json.loads(args.dataset.read_text(encoding="utf-8"))
    checkpoints = ["english", "typed-decisions"] if args.checkpoint == "both" else [args.checkpoint]
    for checkpoint in checkpoints:
        print(json.dumps(evaluate(checkpoint, cases, args.device), indent=2))
