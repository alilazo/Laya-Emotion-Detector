"""Small OpenAI-compatible client for the local Ollama chat model."""

import json
from time import perf_counter

import httpx

from .config import Settings
from .reply import ChatReply, ReplyStream, split_thinking

SYSTEM_PROMPT = "You are a helpful conversational assistant. Reply clearly and naturally."
MAX_CONTEXT_CHARS = 48000
MAX_CONTEXT_MESSAGES = 24


class ChatModelError(Exception):
    pass


def chat_messages(history: list[dict]) -> list[dict[str, str]]:
    """Keep recent user/assistant turns, always including the newest message."""
    selected: list[dict[str, str]] = []
    remaining = MAX_CONTEXT_CHARS
    for item in reversed(history):
        if len(selected) >= MAX_CONTEXT_MESSAGES or remaining <= 0:
            break
        if item["role"] not in {"user", "assistant"}:
            continue
        content = split_thinking(item["content"]).content if item["role"] == "assistant" else item["content"]
        if not content:
            continue
        if len(content) > remaining:
            if selected:
                break
            content = content[-remaining:]
        selected.append({"role": item["role"], "content": content})
        remaining -= len(content)
    selected.reverse()
    return [{"role": "system", "content": SYSTEM_PROMPT}, *selected]


class OllamaChatModel:
    def __init__(self, settings: Settings):
        self.model = settings.ollama_model
        self.client = httpx.AsyncClient(
            base_url=settings.ollama_base_url.rstrip("/") + "/",
            timeout=settings.ollama_timeout_seconds,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def status(self) -> str:
        try:
            response = await self.client.get("models", timeout=5)
            response.raise_for_status()
            ids = {item.get("id") for item in response.json().get("data", [])}
            return "ready" if self.model in ids else "model_missing"
        except (httpx.HTTPError, ValueError, KeyError):
            return "unavailable"

    async def reply(self, history: list[dict]) -> ChatReply:
        started = perf_counter()
        try:
            async with self.client.stream(
                "POST",
                "chat/completions",
                json={"model": self.model, "messages": chat_messages(history), "stream": True},
            ) as response:
                response.raise_for_status()
                stream = ReplyStream()
                if "application/json" in response.headers.get("content-type", ""):
                    # Compatible servers may ignore stream=True. Their thinking time is unknown.
                    await response.aread()
                    message = response.json()["choices"][0]["message"]
                    content = message.get("content") or ""
                    reasoning = reasoning_text(message)
                    if not isinstance(content, str):
                        raise TypeError("Unexpected content")
                    result = split_thinking(content)
                    result.reasoning = "\n\n".join(part for part in (reasoning, result.reasoning) if part) or None
                    result.response_ms = (perf_counter() - started) * 1000
                else:
                    finished = False
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            finished = True
                            break
                        event = json.loads(payload)
                        if event.get("error"):
                            raise ChatModelError("Ollama could not finish the reply. Your message was saved.")
                        for choice in event.get("choices", []):
                            if choice.get("index", 0) != 0:
                                continue
                            delta = choice.get("delta", {})
                            content = delta.get("content") or ""
                            if not isinstance(content, str):
                                raise TypeError("Unexpected content")
                            stream.add(content, reasoning_text(delta), perf_counter())
                            if choice.get("finish_reason") is not None:
                                finished = True
                    if not finished:
                        raise ChatModelError("Ollama stopped before completing the reply. Your message was saved.")
                    result = stream.finish((perf_counter() - started) * 1000)
            if not result.content:
                raise ChatModelError("Ollama returned an empty response.")
            return result
        except httpx.TimeoutException as exc:
            raise ChatModelError("Ollama timed out. Your message was saved; check that the model is running.") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ChatModelError(
                f"Ollama returned HTTP {status} for {self.model}. Your message was saved; check the model and server."
            ) from exc
        except httpx.RequestError as exc:
            raise ChatModelError("Ollama is unavailable. Your message was saved; start Ollama and try again.") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ChatModelError("Ollama returned an unexpected response. Your message was saved.") from exc


def reasoning_text(message: dict) -> str:
    for name in ("reasoning", "reasoning_content", "thinking"):
        value = message.get(name)
        if isinstance(value, str) and value:
            return value
    return ""
