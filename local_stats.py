"""Derives 'today' message/token counts from Claude Code's own local session
transcripts (~/.claude/projects/**/*.jsonl) — no network call needed.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass
class TodayStats:
    messages: int
    tokens: int


def _is_today_local(iso_ts: str, today_local_date) -> bool:
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return False
    return dt.astimezone().date() == today_local_date


def _is_real_user_message(entry: dict) -> bool:
    if entry.get("isSidechain"):
        return False
    message = entry.get("message") or {}
    if message.get("role") != "user":
        return False
    content = message.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(block.get("type") == "text" and block.get("text", "").strip() for block in content)
    return False


def _turn_tokens(usage: dict) -> int:
    return (
        usage.get("input_tokens", 0)
        + usage.get("output_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )


def today_stats() -> TodayStats:
    if not PROJECTS_DIR.exists():
        return TodayStats(messages=0, tokens=0)

    today_local_date = datetime.now().astimezone().date()
    messages = 0
    tokens = 0
    seen_message_ids: set[str] = set()

    for path in PROJECTS_DIR.glob("*/*.jsonl"):
        try:
            if datetime.fromtimestamp(path.stat().st_mtime).date() != today_local_date:
                # File wasn't touched today -> can't contain today's entries.
                continue
        except OSError:
            continue

        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    ts = entry.get("timestamp")
                    if not ts or not _is_today_local(ts, today_local_date):
                        continue

                    etype = entry.get("type")
                    if etype == "user" and _is_real_user_message(entry):
                        messages += 1
                    elif etype == "assistant":
                        msg_id = (entry.get("message") or {}).get("id")
                        if msg_id and msg_id in seen_message_ids:
                            continue
                        if msg_id:
                            seen_message_ids.add(msg_id)
                        usage = (entry.get("message") or {}).get("usage") or {}
                        tokens += _turn_tokens(usage)
        except OSError:
            continue

    return TodayStats(messages=messages, tokens=tokens)


if __name__ == "__main__":
    s = today_stats()
    print(f"messages={s.messages} tokens={s.tokens}")
