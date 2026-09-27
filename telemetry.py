from __future__ import annotations
"""Per-run API telemetry used by the experimental validation harness.

This is deliberately lightweight: production agents keep using the normal
OpenAI client, while the shared client wrapper records model calls, tokens,
latency, and errors whenever an evaluation run opens a telemetry context.
"""
from contextvars import ContextVar
from dataclasses import dataclass, field
import time


_CURRENT: ContextVar["Telemetry" | None] = ContextVar("eval_telemetry", default=None)


@dataclass
class Telemetry:
    calls: list[dict] = field(default_factory=list)

    def record(self, *, api: str, model: str, started: float, response=None, error=None):
        usage = getattr(response, "usage", None) if response is not None else None
        prompt = getattr(usage, "prompt_tokens", None) if usage else None
        completion = getattr(usage, "completion_tokens", None) if usage else None
        total = getattr(usage, "total_tokens", None) if usage else None
        if prompt is None and usage is not None:
            prompt = getattr(usage, "input_tokens", None)
        if completion is None and usage is not None:
            completion = getattr(usage, "output_tokens", None)
        self.calls.append({
            "api": api,
            "model": model,
            "latency_seconds": round(time.time() - started, 4),
            "input_tokens": prompt or 0,
            "output_tokens": completion or 0,
            "total_tokens": total if total is not None else (prompt or 0) + (completion or 0),
            "success": error is None,
            "error": str(error) if error else None,
        })

    @property
    def llm_calls(self):
        return sum(1 for c in self.calls if c["api"] != "embeddings")

    @property
    def embedding_calls(self):
        return sum(1 for c in self.calls if c["api"] == "embeddings")

    @property
    def input_tokens(self):
        return sum(c["input_tokens"] for c in self.calls)

    @property
    def output_tokens(self):
        return sum(c["output_tokens"] for c in self.calls)

    @property
    def total_tokens(self):
        return self.input_tokens + self.output_tokens

    @property
    def latency_seconds(self):
        return round(sum(c["latency_seconds"] for c in self.calls), 4)

    def snapshot(self):
        return {
            "llm_calls": self.llm_calls,
            "embedding_calls": self.embedding_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "api_calls": list(self.calls),
        }


def start_run():
    telemetry = Telemetry()
    token = _CURRENT.set(telemetry)
    return telemetry, token


def end_run(token):
    _CURRENT.reset(token)


def record_call(**kwargs):
    telemetry = _CURRENT.get()
    if telemetry is not None:
        telemetry.record(**kwargs)
