import asyncio
import json

import httpx
import pytest
from app.chat_model import ChatModelError, OllamaChatModel, chat_messages
from app.config import Settings


def test_context_keeps_newest_turn_and_role_order():
    history = [{"role": "user", "content": "x" * 3000} for _ in range(30)]
    history[-2] = {"role": "assistant", "content": "Earlier reply"}
    history[-1] = {"role": "user", "content": "Current question"}
    messages = chat_messages(history)
    assert messages[0]["role"] == "system"
    assert messages[-2:] == [
        {"role": "assistant", "content": "Earlier reply"},
        {"role": "user", "content": "Current question"},
    ]
    assert len(messages) <= 25
    assert sum(len(item["content"]) for item in messages[1:]) <= 48000


def test_openai_compatible_request_and_missing_model():
    captured = []

    def handler(request: httpx.Request):
        captured.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "lfm2.5-8b-a1b:32k"}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "  Hello from Ollama.  "}}]})

    async def run():
        model = OllamaChatModel(Settings(ollama_base_url="http://127.0.0.1:11434/v1"))
        await model.client.aclose()
        model.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:11434/v1/")
        try:
            assert await model.status() == "ready"
            reply = await model.reply([{"role": "user", "content": "Hello"}])
            assert reply.content == "Hello from Ollama."
            assert reply.thinking_ms is None
            assert reply.response_ms >= 0
        finally:
            await model.close()

    asyncio.run(run())
    assert captured[0].url.path == "/v1/models"
    assert captured[1].url.path == "/v1/chat/completions"
    body = json.loads(captured[1].content)
    assert body["model"] == "lfm2.5-8b-a1b:32k"
    assert body["messages"][-1] == {"role": "user", "content": "Hello"}
    assert body["stream"] is True


@pytest.mark.parametrize("tagged", [True, False])
def test_stream_separates_thinking_from_answer(tagged):
    if tagged:
        deltas = [{"content": part} for part in ["<thi", "nk>Let me check.", "</thi", "nk>", "The answer is 4."]]
    else:
        deltas = [{"reasoning": "Let me check."}, {"content": "The answer is 4."}]
    events = [{"choices": [{"index": 0, "delta": delta}]} for delta in deltas]
    events.append({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
    body = "".join(f"data: {json.dumps(event)}\n\n" for event in events) + "data: [DONE]\n\n"

    async def run():
        model = OllamaChatModel(Settings())
        await model.client.aclose()
        model.client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)
            ),
            base_url="http://127.0.0.1:11434/v1/",
        )
        try:
            reply = await model.reply([{"role": "user", "content": "What is 2 + 2?"}])
            assert reply.content == "The answer is 4."
            assert reply.reasoning == "Let me check."
            assert 0 <= reply.thinking_ms <= reply.response_ms
        finally:
            await model.close()

    asyncio.run(run())


def test_interrupted_stream_does_not_save_a_partial_reply():
    async def run():
        model = OllamaChatModel(Settings())
        await model.client.aclose()
        model.client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    headers={"content-type": "text/event-stream"},
                    content='data: {"choices":[{"delta":{"content":"Partial answer"}}]}\n\n',
                )
            ),
            base_url="http://127.0.0.1:11434/v1/",
        )
        try:
            with pytest.raises(ChatModelError, match="stopped before completing"):
                await model.reply([{"role": "user", "content": "Hello"}])
        finally:
            await model.close()

    asyncio.run(run())


def test_ollama_http_error_is_actionable():
    async def run():
        model = OllamaChatModel(Settings())
        await model.client.aclose()
        model.client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(404, json={"error": "not found"})),
            base_url="http://127.0.0.1:11434/v1/",
        )
        try:
            with pytest.raises(ChatModelError, match="HTTP 404"):
                await model.reply([{"role": "user", "content": "Hello"}])
        finally:
            await model.close()

    asyncio.run(run())
