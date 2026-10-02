"""Check a local evidence model on authored cases without writing chat history."""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import ROOT, Settings
from app.evidence import EvidenceError, EvidenceVerifier

NEUTRAL = {"anxiety": False, "sadness": False, "fear": False}
CASES = [
    ("I really miss my dog today.", {"anxiety": False, "sadness": True, "fear": False}),
    ("Yeah it's been sad for me lately", {"anxiety": False, "sadness": True, "fear": False}),
    ("Okay but I am also really scared for her", {"anxiety": False, "sadness": False, "fear": True}),
    ("I am worried about tomorrow's interview.", {"anxiety": True, "sadness": False, "fear": False}),
    ("I am not sad, anxious, or scared. I feel fine.", NEUTRAL),
    ("My friend is scared and sad. I feel calm.", NEUTRAL),
    ('In the novel, the character says, "I am scared and lonely."', NEUTRAL),
    ("If I lost my dog, I might be sad, but she is here and I feel happy.", NEUTRAL),
    ("I was anxious last week, but now I feel calm.", NEUTRAL),
    ("I watered the plants and made lunch.", NEUTRAL),
]


def check(settings: Settings) -> dict:
    verifier = EvidenceVerifier(settings)
    results = []
    try:
        for text, expected in CASES:
            started = perf_counter()
            try:
                result = verifier.verify({"current_user_message": text, "recent_context": []})
            except EvidenceError as exc:
                results.append({
                    "text": text,
                    "elapsed_ms": round((perf_counter() - started) * 1000),
                    "passed": False,
                    "error": str(exc),
                })
                continue
            results.append({
                "text": text,
                "elapsed_ms": round((perf_counter() - started) * 1000),
                "passed": all(bool(result[key]["level"]) == value for key, value in expected.items()),
                "evidence": result,
            })
    finally:
        verifier.close()
    return {
        "model": settings.emotion_verifier_model,
        "passed": sum(item["passed"] for item in results),
        "total": len(results),
        "cases": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Installed Ollama model; defaults to EMOTION_VERIFIER_MODEL or the app default")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "verifier-smoke.json")
    args = parser.parse_args()
    settings = Settings()
    if args.model:
        settings = replace(settings, emotion_verifier_model=args.model)
    report = check(settings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] == report["total"] else 1)
