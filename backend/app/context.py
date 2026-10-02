import json
import re


def _tokens(text: str) -> int:
    # Conservative approximation; model tokenizer gets final say.
    return max(1, len(re.findall(r"\w+|[^\w\s]", text)))


def _clip_ends(text: str, budget: int) -> str:
    parts = re.findall(r"\w+|[^\w\s]|\s+", text)
    if _tokens(text) <= budget:
        return text
    head = max(1, budget // 2)
    tail = max(1, budget - head)
    meaningful = [i for i, part in enumerate(parts) if not part.isspace()]
    left = parts[: meaningful[min(head, len(meaningful) - 1)] + 1]
    right = parts[meaningful[max(0, len(meaningful) - tail)] :]
    return "".join(left).rstrip() + " … [middle omitted] … " + "".join(right).lstrip()


def build_emotion_context(current_user_message: str, recent_context: list[dict], budget: int = 650) -> dict:
    """Keep current user text first; use recent turns only if they fit."""
    current = _clip_ends(current_user_message, max(80, budget - 70))
    state = {"evaluation_scope": "CURRENT_USER_MESSAGE", "recent_context": [], "current_user_message": current}
    used = _tokens(json.dumps(state))
    for turn in reversed(recent_context):
        if turn.get("role") not in {"user", "assistant"}:
            continue
        candidate = {"role": turn["role"], "content": turn.get("content", "")}
        cost = _tokens(json.dumps(candidate))
        if used + cost > budget:
            break
        state["recent_context"].insert(0, candidate)
        used += cost
    return state
