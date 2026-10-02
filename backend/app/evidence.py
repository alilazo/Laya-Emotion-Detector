"""Check who expresses each emotion before applying a Laya intensity score."""

import json

import httpx

from .config import Settings
from .gauge import EMOTIONS

EVIDENCE_VERSION = "evidence-v1"
EVIDENCE_PROMPT = """Evaluate only emotions personally expressed by the CURRENT USER MESSAGE.
The recent conversation may clarify a reference or a short answer. It must not supply an emotion
missing from the current message. Do not adopt feelings suggested by the assistant. Never infer
death, danger, diagnosis, or another unstated event. A feeling attributed to someone else, a
fictional or quoted speaker, a hypothetical example, a negated feeling, and a resolved past
feeling do not count as the user's current feeling.

Score each signal INDEPENDENTLY: anxiety means anticipatory worry, nervousness, or rumination;
sadness means sorrow, missing someone, emotional hurt, grief, disappointment, or loneliness;
fear means personally feeling scared, afraid, unsafe, or threatened. Fear alone does not prove
anxiety or sadness. Worry alone does not prove fear or sadness. A sad situation does not prove
worry or fear.

Use level 0 when absent or unsupported, 1 for slight, 2 for clear moderate, 3 for strong, and
4 for overwhelming. Choose the lower supported level if uncertain. Every positive level needs
a short VERBATIM quote from the current user message that supports this emotion. Use an empty
evidence string for level 0. Quotes about someone else's feeling do not support the user's score.

Return only the requested JSON fields."""

EMOTION_SCHEMA = {
    "type": "object",
    "properties": {
        key: {
            "type": "object",
            "properties": {
                "level": {"type": "integer", "minimum": 0, "maximum": 4},
                "evidence": {"type": "string"},
            },
            "required": ["level", "evidence"],
            "additionalProperties": False,
        }
        for key in EMOTIONS
    },
    "required": list(EMOTIONS),
    "additionalProperties": False,
}


class EvidenceError(RuntimeError):
    pass


def quote_in_message(quote: str, message: str) -> bool:
    """Permit an abbreviated verbatim quote while rejecting invented evidence."""
    cursor = 0
    parts = [part.strip() for part in quote.replace("…", "...").split("...") if part.strip()]
    if not parts or any(len(part) < 4 for part in parts):
        return False
    text = message.casefold()
    for part in parts:
        found = text.find(part.casefold(), cursor)
        if found < 0:
            return False
        cursor = found + len(part)
    return True


class EvidenceVerifier:
    def __init__(self, settings: Settings):
        self.model = settings.emotion_verifier_model
        self.client = httpx.Client(
            base_url=settings.ollama_base_url.rstrip("/") + "/",
            timeout=settings.ollama_timeout_seconds,
        )

    def close(self) -> None:
        self.client.close()

    def status(self) -> str:
        try:
            response = self.client.get("models", timeout=5)
            response.raise_for_status()
            ids = {item.get("id") for item in response.json().get("data", [])}
            return "ready" if self.model in ids else "model_missing"
        except (httpx.HTTPError, ValueError, KeyError):
            return "unavailable"

    def verify(self, state: dict) -> dict:
        current = state["current_user_message"]
        primary = {"evaluation_scope": "CURRENT_USER_MESSAGE", "current_user_message": current, "recent_context": []}
        result = self._request(primary)
        # A terse affirmative can require the previous turn to identify what "yes" refers to.
        # Explicit emotion statements are judged without older text, which otherwise leaks into the score.
        first_word = current.lstrip().split(maxsplit=1)[0].strip(".,!?;:").casefold() if current.strip() else ""
        if (
            not any(result[key]["level"] for key in EMOTIONS)
            and len(current.split()) <= 8
            and first_word in {"yes", "yeah", "it", "that", "same", "still"}
            and state.get("recent_context")
        ):
            return self._request(state)
        return result

    def _request(self, state: dict) -> dict:
        try:
            response = self.client.post(
                "chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": EVIDENCE_PROMPT},
                        {"role": "user", "content": json.dumps(state, ensure_ascii=False)},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {"name": "emotion_evidence", "strict": True, "schema": EMOTION_SCHEMA},
                    },
                    "temperature": 0,
                    "seed": 17,
                    "reasoning_effort": "none",
                    "max_tokens": 800,
                    "stream": False,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
            current = state["current_user_message"]
            if set(result) != set(EMOTIONS):
                raise EvidenceError("Evidence response is incomplete")
            for key in EMOTIONS:
                item = result[key]
                level, quote = item["level"], item["evidence"]
                if type(level) is not int or not 0 <= level <= 4 or not isinstance(quote, str):
                    raise EvidenceError(f"Invalid {key} evidence")
                if level and not quote_in_message(quote, current):
                    raise EvidenceError(f"Unsupported {key} evidence")
                if not level:
                    item["evidence"] = ""
            return result
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise EvidenceError(f"Emotion evidence check failed: {type(exc).__name__}") from exc
