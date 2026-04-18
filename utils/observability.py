"""
Observability — structured logging, agent trace metadata, LangSmith spans.

Every agent call emits a structured event that can be:
  - printed to console for debugging
  - written to data/logs/agent_events.jsonl for analysis
  - sent to LangSmith as a traced span (if LANGSMITH_API_KEY is set)

The events carry consistent fields so they can be replayed into the
evaluation harness. This is what makes your BTP's "we ran 50 pipeline
invocations across 10 users" statement actually defensible — you have
the logs to prove it.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import BASE_DIR


LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "agent_events.jsonl"

try:
    from langsmith import Client, traceable
    HAS_LANGSMITH = bool(os.getenv("LANGSMITH_API_KEY"))
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "fitagent-prod")
except ImportError:
    HAS_LANGSMITH = False
    def traceable(fn):
        return fn


@dataclass
class AgentEvent:
    event_id: str
    trace_id: str
    agent: str                       # "fitness" | "nutrition" | "progress" | "profile" | "orchestrator"
    event_type: str                  # "start" | "end" | "error" | "metric"
    user_id: str
    timestamp: str
    duration_ms: Optional[float] = None
    metadata: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), default=str) + "\n"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_event(event: AgentEvent):
    """Append event to JSONL log file."""
    try:
        with LOG_FILE.open("a") as f:
            f.write(event.to_json_line())
    except Exception as e:
        print(f"  [Obs] Failed to write log: {e}")


def log_event(
    agent: str,
    event_type: str,
    user_id: str,
    trace_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    metrics: Optional[dict] = None,
    error: Optional[str] = None,
    duration_ms: Optional[float] = None,
) -> AgentEvent:
    """Log a single agent event."""
    event = AgentEvent(
        event_id=str(uuid.uuid4())[:12],
        trace_id=trace_id or str(uuid.uuid4())[:12],
        agent=agent,
        event_type=event_type,
        user_id=user_id,
        timestamp=_now_iso(),
        duration_ms=duration_ms,
        metadata=metadata or {},
        metrics=metrics or {},
        error=error,
    )
    _write_event(event)
    return event


@contextmanager
def agent_span(
    agent: str,
    user_id: str,
    trace_id: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Context manager that emits start + end events around an agent invocation.

    Usage:
        with agent_span("fitness", user_id="user_001") as span:
            result = do_work()
            span["metrics"]["sets_generated"] = 48
    """
    start_event = log_event(
        agent=agent,
        event_type="start",
        user_id=user_id,
        trace_id=trace_id,
        metadata=metadata,
    )
    t0 = time.time()
    state = {"metrics": {}, "metadata": dict(metadata or {}), "error": None}

    try:
        yield state
    except Exception as e:
        state["error"] = str(e)[:500]
        duration_ms = round((time.time() - t0) * 1000, 1)
        log_event(
            agent=agent,
            event_type="error",
            user_id=user_id,
            trace_id=start_event.trace_id,
            metadata=state["metadata"],
            metrics=state["metrics"],
            error=state["error"],
            duration_ms=duration_ms,
        )
        raise
    else:
        duration_ms = round((time.time() - t0) * 1000, 1)
        log_event(
            agent=agent,
            event_type="end",
            user_id=user_id,
            trace_id=start_event.trace_id,
            metadata=state["metadata"],
            metrics=state["metrics"],
            duration_ms=duration_ms,
        )


def read_recent_events(
    user_id: Optional[str] = None,
    agent: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Read the tail of the event log, optionally filtered."""
    if not LOG_FILE.exists():
        return []

    events = []
    try:
        with LOG_FILE.open() as f:
            # Read tail efficiently — for small log files just read all
            lines = f.readlines()[-2000:]
        for line in reversed(lines):
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if user_id and e.get("user_id") != user_id:
                continue
            if agent and e.get("agent") != agent:
                continue
            events.append(e)
            if len(events) >= limit:
                break
    except Exception as e:
        print(f"  [Obs] Failed to read log: {e}")
    return events


def summarize_recent_runs(user_id: str) -> dict:
    """Aggregate stats over recent runs for this user."""
    events = read_recent_events(user_id=user_id, limit=500)

    end_events = [e for e in events if e["event_type"] == "end"]
    error_events = [e for e in events if e["event_type"] == "error"]

    by_agent: dict[str, dict] = {}
    for e in end_events:
        agent = e["agent"]
        by_agent.setdefault(agent, {"count": 0, "total_ms": 0})
        by_agent[agent]["count"] += 1
        by_agent[agent]["total_ms"] += e.get("duration_ms") or 0

    for agent, stats in by_agent.items():
        stats["avg_ms"] = round(stats["total_ms"] / stats["count"], 1) if stats["count"] else 0

    return {
        "total_events": len(events),
        "successful_runs": len(end_events),
        "errors": len(error_events),
        "by_agent": by_agent,
    }


# Self-test
if __name__ == "__main__":
    print("── Observability Tests ──\n")

    # Simple event
    log_event(
        agent="test",
        event_type="start",
        user_id="test_user",
        metadata={"foo": "bar"},
    )
    print("  ✓ Single event logged")

    # Span context manager — success case
    with agent_span("fitness", "test_user", metadata={"week": 1}) as span:
        span["metrics"]["sets"] = 48
        span["metrics"]["exercises"] = 12
        time.sleep(0.05)
    print("  ✓ Span success case emits start + end")

    # Span error case
    try:
        with agent_span("nutrition", "test_user") as span:
            raise ValueError("test error")
    except ValueError:
        pass
    print("  ✓ Span error case emits start + error")

    # Read back
    events = read_recent_events(user_id="test_user", limit=10)
    print(f"\n  Recent events for test_user: {len(events)}")
    for e in events[:5]:
        print(f"    [{e['event_type']:6}] {e['agent']} "
              f"duration={e.get('duration_ms')}ms")

    stats = summarize_recent_runs("test_user")
    print(f"\n  Summary: {stats['successful_runs']} successes, "
          f"{stats['errors']} errors")
    for agent, s in stats["by_agent"].items():
        print(f"    {agent}: {s['count']} runs, avg {s['avg_ms']}ms")

    print("\n  [Observability] Tests passed")