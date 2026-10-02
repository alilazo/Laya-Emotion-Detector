"""Separate model-supplied thinking from the answer, including legacy replies."""

import re
from dataclasses import dataclass

THINK_OPEN = re.compile(r"^\s*<think(?:ing)?>", re.IGNORECASE)
THINK_CLOSE = re.compile(r"</think(?:ing)?>", re.IGNORECASE)


@dataclass
class ChatReply:
    content: str
    reasoning: str | None = None
    thinking_ms: float | None = None
    response_ms: float | None = None


def split_thinking(text: str) -> ChatReply:
    """Read leading thinking blocks; leave tags quoted in the answer alone."""
    remaining, blocks = text, []
    while match := THINK_OPEN.match(remaining):
        remaining = remaining[match.end() :]
        closing = THINK_CLOSE.search(remaining)
        if closing is None:
            blocks.append(remaining.strip())
            remaining = ""
            break
        blocks.append(remaining[: closing.start()].strip())
        remaining = remaining[closing.end() :]
    return ChatReply(remaining.strip(), "\n\n".join(block for block in blocks if block) or None)


def present_message(row: dict) -> dict:
    message = dict(row)
    if message["role"] == "assistant":
        parsed = split_thinking(message["content"])
        message["content"] = parsed.content
        message["reasoning"] = message.get("reasoning") or parsed.reasoning
    return message


class ReplyStream:
    """Measure the observed thinking phase, ending when answer text arrives."""

    def __init__(self):
        self.content = ""
        self.reasoning = ""
        self.thinking_started: float | None = None
        self.answer_started: float | None = None
        self.last_thinking: float | None = None
        self._reasoning_length = 0

    def add(self, content: str, reasoning: str, at: float) -> None:
        self.content += content
        self.reasoning += reasoning
        parsed = split_thinking(self.content)
        length = len(self.reasoning) + len(parsed.reasoning or "")
        if length > self._reasoning_length:
            if self.thinking_started is None:
                self.thinking_started = at
            self.last_thinking = at
            self._reasoning_length = length
        if parsed.content and self.thinking_started is not None and self.answer_started is None:
            self.answer_started = at

    def finish(self, response_ms: float) -> ChatReply:
        parsed = split_thinking(self.content)
        parsed.reasoning = "\n\n".join(part for part in (self.reasoning.strip(), parsed.reasoning) if part) or None
        end = self.answer_started if self.answer_started is not None else self.last_thinking
        if self.thinking_started is not None and end is not None:
            parsed.thinking_ms = max(0.0, (end - self.thinking_started) * 1000)
        parsed.response_ms = response_ms
        return parsed
