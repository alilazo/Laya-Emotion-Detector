from dataclasses import dataclass
from time import perf_counter
from typing import Any

from .config import Settings
from .evidence import EVIDENCE_VERSION, EvidenceVerifier
from .gauge import EMOTIONS, clamp
from .prompts import EMOTION_QUESTIONS


@dataclass
class EmotionPrediction:
    raw: dict[str, float]
    instant: dict[str, float]
    distributions: dict[str, Any]
    inference_ms: float


class EmotionScoreCalibrator:
    def calibrate(self, emotion: str, raw_score: float, supported_level: int) -> float:
        if supported_level == 0:
            return 0.0
        return clamp(raw_score, max(0, supported_level - 0.5), min(4, supported_level + 0.5))


class EmotionModel:
    def __init__(
        self,
        settings: Settings,
        calibrator: EmotionScoreCalibrator | None = None,
        verifier: EvidenceVerifier | None = None,
    ):
        self.settings = settings
        self.calibrator = calibrator or EmotionScoreCalibrator()
        self.verifier = verifier or EvidenceVerifier(settings)
        self.agent = None
        self.error: str | None = None

    def load(self) -> None:
        if not self.settings.laya_enabled:
            self.error = "Laya disabled by configuration"
            return
        try:
            import laya

            kwargs = {} if self.settings.device == "auto" else {"device": self.settings.device}
            if self.settings.checkpoint == "typed-decisions":
                kwargs["subfolder"] = "typed-decisions"
            self.agent = laya.load("convaiinnovations/laya", **kwargs)
            self.error = None
            if self.settings.warmup:
                self.agent.predict("Hello.", EMOTION_QUESTIONS)
        except Exception as exc:  # noqa: BLE001 - model load failure must not stop chat startup
            self.agent = None
            self.error = f"{type(exc).__name__}: {exc}"

    @property
    def ready(self) -> bool:
        return self.agent is not None

    def close(self) -> None:
        self.verifier.close()

    def predict(self, state: dict) -> EmotionPrediction:
        if self.agent is None:
            raise RuntimeError(self.error or "Laya is not loaded")
        start = perf_counter()
        result = self.agent.predict(state, EMOTION_QUESTIONS)
        evidence = self.verifier.verify(state)
        answers = result["answers"]
        raw, instant, distributions = {}, {}, {}
        for key in EMOTIONS:
            score = clamp(float(answers[key]["score"]), 0, 4)
            raw[key] = score
            instant[key] = self.calibrator.calibrate(key, score, evidence[key]["level"]) * 25
            distributions[key] = answers[key].get("probabilities")
        distributions["evidence"] = {"version": EVIDENCE_VERSION, "model": self.settings.emotion_verifier_model, **evidence}
        return EmotionPrediction(raw, instant, distributions, (perf_counter() - start) * 1000)
