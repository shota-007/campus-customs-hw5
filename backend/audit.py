"""Append-only audit trail: output/audit_trail.json.

Every step of every agent loop is appended as one AuditEvent. The file is a
JSON array that only ever grows. Runs never wipe it, and a reset of the
database does not touch it either.
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from .config import AUDIT_TEXT_LIMIT, AUDIT_TRAIL_PATH
from .models import AuditEvent, TeamDeps

_lock = threading.Lock()


def _clip(value: Any) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) <= AUDIT_TEXT_LIMIT:
        return value
    return text[:AUDIT_TEXT_LIMIT] + f"... [clipped, {len(text)} chars total]"


def append_event(event: AuditEvent) -> None:
    """Append one event, rewriting the file atomically so a crash can't leave half a JSON array."""
    with _lock:
        AUDIT_TRAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
        events: list = []
        if AUDIT_TRAIL_PATH.exists() and AUDIT_TRAIL_PATH.stat().st_size:
            events = json.loads(AUDIT_TRAIL_PATH.read_text(encoding="utf-8"))
        events.append(event.model_dump(mode="json"))
        tmp = AUDIT_TRAIL_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, AUDIT_TRAIL_PATH)


def record(deps: TeamDeps, step: int, event: str, *, model: str | None = None,
           detail: dict | None = None, usage: Any = None) -> None:
    append_event(
        AuditEvent(
            ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            run_id=deps.run_id,
            agent_run_id=deps.agent_run_id,
            ticket_id=deps.ticket_id,
            agent=deps.agent,
            chain=list(deps.chain),
            depth=deps.depth,
            step=step,
            event=event,
            model=model,
            detail=detail or {},
            usage=_usage_dict(usage),
        )
    )


def record_human(event: str, *, ticket_id: int | None = None, actor: str = "human", detail: dict | None = None) -> None:
    """Audit a dashboard action (approval, rejection, reset) that no agent took."""
    append_event(
        AuditEvent(
            ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            run_id=f"{actor}-action",
            agent_run_id="",
            ticket_id=ticket_id,
            agent=actor,
            chain=[actor],
            depth=0,
            step=0,
            event=event,
            detail=detail or {},
        )
    )


def read_events() -> list[dict]:
    with _lock:
        if not AUDIT_TRAIL_PATH.exists() or not AUDIT_TRAIL_PATH.stat().st_size:
            return []
        return json.loads(AUDIT_TRAIL_PATH.read_text(encoding="utf-8"))


def _usage_dict(usage: Any) -> dict:
    if usage is None:
        return {}
    return {
        "requests": usage.requests,
        "tool_calls": getattr(usage, "tool_calls", None),
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.input_tokens + usage.output_tokens,
    }


def describe_request(request: ModelRequest) -> dict:
    """What went *into* the model this step: the prompt, tool results, or retry notes."""
    parts = []
    for p in request.parts:
        if isinstance(p, UserPromptPart):
            parts.append({"type": "user_prompt", "content": _clip(p.content)})
        elif isinstance(p, ToolReturnPart):
            parts.append({"type": "tool_return", "tool": p.tool_name, "tool_call_id": p.tool_call_id,
                          "content": _clip(p.content)})
        elif isinstance(p, RetryPromptPart):
            parts.append({"type": "tool_error_or_retry", "tool": p.tool_name, "tool_call_id": p.tool_call_id,
                          "content": _clip(p.model_response())})
    return {"parts": parts}


def describe_response(response: ModelResponse) -> dict:
    """What came *out* of the model this step: text, tool calls (with args), thinking size."""
    parts = []
    for p in response.parts:
        if isinstance(p, ToolCallPart):
            parts.append({"type": "tool_call", "tool": p.tool_name, "tool_call_id": p.tool_call_id, "args": _clip(p.args_as_dict())})
        elif isinstance(p, TextPart):
            parts.append({"type": "text", "content": _clip(p.content)})
        elif isinstance(p, ThinkingPart):
            parts.append({"type": "thinking", "chars": len(p.content or "")})
    return {
        "parts": parts,
        "served_model": response.model_name,
        "step_tokens": {"input": response.usage.input_tokens, "output": response.usage.output_tokens},
        "finish_reason": getattr(response, "finish_reason", None),
    }


def describe_node(node: Any) -> tuple[str, dict]:
    if Agent.is_user_prompt_node(node):
        return "user_prompt", {"prompt": _clip(node.user_prompt)}
    if Agent.is_model_request_node(node):
        return "model_request", describe_request(node.request)
    if Agent.is_call_tools_node(node):
        return "model_response", describe_response(node.model_response)
    if Agent.is_end_node(node):
        output = node.data.output
        return "run_end", {"output": output.model_dump(mode="json") if hasattr(output, "model_dump") else _clip(output)}
    return type(node).__name__, {}
