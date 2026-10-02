import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("EMOTION_DB_PATH", ROOT / "data" / "showcase.sqlite3"))
    checkpoint: str = os.getenv("LAYA_CHECKPOINT", "typed-decisions")
    device: str = os.getenv("LAYA_DEVICE", "auto")
    laya_enabled: bool = os.getenv("LAYA_ENABLED", "1") == "1"
    warmup: bool = os.getenv("LAYA_WARMUP", "1") == "1"
    neutral_threshold: float = float(os.getenv("EMOTION_NEUTRAL_THRESHOLD", "10"))
    mixed_threshold: float = float(os.getenv("EMOTION_MIXED_THRESHOLD", "60"))
    high_threshold: float = float(os.getenv("EMOTION_HIGH_THRESHOLD", "70"))
    access_token: str = os.getenv("LOCAL_ACCESS_TOKEN", "")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "lfm2.5-8b-a1b:32k")
    emotion_verifier_model: str = os.getenv("EMOTION_VERIFIER_MODEL", "qwen3.6-35b-a3b:ud-iq3-s")
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))

    def __post_init__(self) -> None:
        if self.checkpoint not in {"typed-decisions", "english"}:
            raise ValueError("LAYA_CHECKPOINT must be typed-decisions or english")
        if self.device not in {"auto", "cpu", "cuda", "mps", "xpu"}:
            raise ValueError("LAYA_DEVICE must be auto, cpu, cuda, mps, or xpu")
        if not self.ollama_base_url.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL must be an HTTP(S) URL")
        if not self.ollama_model.strip():
            raise ValueError("OLLAMA_MODEL cannot be blank")
        if not self.emotion_verifier_model.strip():
            raise ValueError("EMOTION_VERIFIER_MODEL cannot be blank")
        if self.ollama_timeout_seconds <= 0:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be positive")
