from math import isfinite

EMOTIONS = ("anxiety", "sadness", "fear")


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    if not isfinite(value):
        raise ValueError("emotion score must be finite")
    return min(high, max(low, value))


def update_emotion_gauge(previous: float, instant: float) -> float:
    previous, instant = clamp(previous), clamp(instant)
    if previous == 0 and instant >= 50:
        return instant
    delta = instant - previous
    alpha = 0.70 if instant >= 80 and delta >= 30 else (0.55 if delta > 0 else 0.12)
    return clamp(previous + alpha * delta)


def update_gauges(previous: dict[str, float], instant: dict[str, float], first: bool) -> dict[str, float]:
    return {
        key: clamp(instant[key]) if first else update_emotion_gauge(previous[key], instant[key]) for key in EMOTIONS
    }
