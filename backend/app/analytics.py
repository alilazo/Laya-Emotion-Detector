from math import sqrt

from .gauge import EMOTIONS, clamp


def metrics(values: dict[str, float], neutral_threshold: float = 10, mixed_threshold: float = 60) -> dict:
    clean = {key: clamp(float(values[key])) for key in EMOTIONS}
    total = sum(clean.values())
    neutral = all(value < neutral_threshold for value in clean.values())
    weights = {key: clean[key] / total if total and not neutral else 1 / 3 for key in EMOTIONS}
    intensity = sqrt(sum(value * value for value in clean.values()) / 3)
    dominant = "neutral" if neutral else max(EMOTIONS, key=lambda key: clean[key])
    return {
        "values": clean,
        "position": weights,
        "overallIntensity": intensity,
        "dominantEmotion": dominant,
        "mixed": sum(value >= mixed_threshold for value in clean.values()) >= 2,
        "neutral": neutral,
    }


def values_for_mode(chat: dict, mode: str) -> dict[str, float]:
    if mode not in {"final", "peak", "average"}:
        raise ValueError("Invalid mode")
    prefix = "current" if mode == "final" else mode
    return {key: float(chat[f"{prefix}_{key}"]) for key in EMOTIONS}
