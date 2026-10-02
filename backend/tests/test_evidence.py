import json

import httpx
import pytest
from app.config import Settings
from app.evidence import EvidenceError, EvidenceVerifier


def test_verifier_uses_current_message_and_rejects_prior_quotes():
    seen = []

    def handler(request):
        payload = json.loads(request.content)
        seen.append(json.loads(payload["messages"][1]["content"]))
        content = {
            "anxiety": {"level": 0, "evidence": ""},
            "sadness": {"level": 2, "evidence": "it's been sad for me"},
            "fear": {"level": 0, "evidence": ""},
        }
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}]})

    verifier = EvidenceVerifier(Settings())
    verifier.client.close()
    verifier.client = httpx.Client(base_url="http://127.0.0.1:11434/v1/", transport=httpx.MockTransport(handler))
    try:
        result = verifier.verify(
            {
                "evaluation_scope": "CURRENT_USER_MESSAGE",
                "current_user_message": "Yeah it's been sad for me lately",
                "recent_context": [{"role": "user", "content": "I really miss my dog today."}],
            }
        )
    finally:
        verifier.close()
    assert result["sadness"]["level"] == 2
    assert seen[0]["recent_context"] == []


def test_verifier_rejects_evidence_only_found_in_prior_message():
    content = {
        "anxiety": {"level": 0, "evidence": ""},
        "sadness": {"level": 3, "evidence": "I really miss my dog today."},
        "fear": {"level": 0, "evidence": ""},
    }
    verifier = EvidenceVerifier(Settings())
    verifier.client.close()
    verifier.client = httpx.Client(
        base_url="http://127.0.0.1:11434/v1/",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}]})
        ),
    )
    try:
        with pytest.raises(EvidenceError, match="Unsupported sadness evidence"):
            verifier.verify({"current_user_message": "I'm fine today.", "recent_context": []})
    finally:
        verifier.close()
