"""Append-only audit trail of agent-loop activity: output/audit_trail.json.

One entry per chat message the agent handles, successful or not:

    {
      "time": "2026-09-27T18:30:12Z",        when the run started (UTC)
      "run_id": "…",                          PydanticAI run id
      "who": "guest" | "user 4",              never a name or email
      "page": "/products/yale-dad-crewneck",
      "message": "Do you have this in L?",    shortened, sensitive data removed
      "steps": [                              the agent loop, in order
        {"time": …, "type": "tool_call",   "tool": "check_stock", "args": "{…}"},
        {"time": …, "type": "tool_result", "tool": "check_stock", "result": "{…}"},
        {"time": …, "type": "retry",       "tool": "fact_check",  "result": "you wrote $70…"},
        {"time": …, "type": "answer",      "tool": "final_result"}   an answer the model
                                                                    handed back (a "retry"
                                                                    after it means it was rejected)
      ],
      "fact_check_retries": 0,
      "stop_reason": "final_response" | "content_filter" | "usage_limit" |
                     "fact_check_failed" | "model_error" | "error",
      "reply": "The Yale Dad Crewneck is sold out in L…",
      "usage": {"requests": 2, "tool_calls": 1, "input_tokens": …, "output_tokens": …},
      "duration_ms": 5321
    }

The file is a JSON array that only grows: each write re-reads it, appends and
atomically replaces it, so a crash mid-write can't truncate it. Nothing in the
app ever deletes entries. A file that isn't valid JSON is moved aside
(audit_trail.corrupt-<time>.json), never overwritten.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)

from safety import scrub_for_log

AUDIT_PATH = Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"
SHORT = 240  # max characters for any message, argument or result preview

_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def short(value: Any, limit: int = SHORT) -> str:
    if value is None:
        return ""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    text = scrub_for_log(" ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _ts(part: Any, message: Any) -> str:
    stamp = getattr(part, "timestamp", None) or getattr(message, "timestamp", None)
    if isinstance(stamp, datetime):
        return stamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return now()


def steps_from(messages: list[ModelMessage], output_tool_names: set[str]) -> list[dict]:
    """The agent loop as a flat list of tool calls, tool results, retries and answers."""
    steps: list[dict] = []
    for message in messages:
        for part in getattr(message, "parts", []):
            if isinstance(message, ModelResponse) and isinstance(part, ToolCallPart):
                if part.tool_name in output_tool_names:
                    steps.append({"time": _ts(part, message), "type": "answer", "tool": part.tool_name})
                else:
                    steps.append({"time": _ts(part, message), "type": "tool_call", "tool": part.tool_name,
                                  "args": short(part.args_as_dict())})
            elif isinstance(message, ModelResponse) and isinstance(part, TextPart) and part.content.strip():
                steps.append({"time": _ts(part, message), "type": "text", "result": short(part.content)})
            elif isinstance(message, ModelRequest) and isinstance(part, ToolReturnPart):
                if part.tool_name in output_tool_names:
                    continue  # "Final result processed." adds nothing
                steps.append({"time": _ts(part, message), "type": "tool_result", "tool": part.tool_name,
                              "result": short(part.content)})
            elif isinstance(message, ModelRequest) and isinstance(part, RetryPromptPart):
                tool = part.tool_name or "output"
                steps.append({"time": _ts(part, message), "type": "retry",
                              "tool": "fact_check" if "Fact-check failed" in str(part.content) else tool,
                              "result": short(part.content)})
    return steps


def append(entry: dict) -> None:
    """Add one entry to the audit trail. Never removes or rewrites earlier entries."""
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        rows: list = []
        if AUDIT_PATH.exists():
            try:
                existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
                if not isinstance(existing, list):
                    raise ValueError("audit trail is not a JSON array")
                rows = existing
            except (json.JSONDecodeError, ValueError, OSError):
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.corrupt-{stamp}.json"))
        rows.append(entry)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)  # atomic: readers see the old file or the new one, never half
