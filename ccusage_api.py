"""Reads Claude Code's own OAuth token from macOS Keychain and fetches
account usage/rate-limit data from Anthropic's (undocumented) usage endpoint.

No browser cookies involved — reuses the same credential the `claude` CLI
already stores after you run `claude login`.
"""
from __future__ import annotations

import json
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone

from i18n import t

KEYCHAIN_SERVICE = "Claude Code-credentials"
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"


class CredentialsError(RuntimeError):
    retry_after: int | None = None


def _read_credentials() -> dict:
    try:
        raw = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError as e:
        raise CredentialsError(t("err_no_creds")) from e

    try:
        return json.loads(raw)["claudeAiOauth"]
    except (json.JSONDecodeError, KeyError) as e:
        raise CredentialsError(t("err_bad_creds")) from e


@dataclass
class Window:
    percent: float
    resets_at: datetime | None
    active: bool

    @property
    def minutes_to_reset(self) -> int | None:
        if self.resets_at is None:
            return None
        delta = self.resets_at - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds() // 60))


@dataclass
class Usage:
    five_hour: Window
    seven_day: Window
    plan: str


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fetch_usage(timeout: float = 10.0) -> Usage:
    creds = _read_credentials()
    token = creds["accessToken"]
    plan = (creds.get("subscriptionType") or "unknown").capitalize()
    req = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 429:
            retry_after_hdr = e.headers.get("Retry-After")
            retry_suffix = t("err_rate_limited_retry", s=retry_after_hdr) if retry_after_hdr else ""
            err = CredentialsError(t("err_rate_limited", retry=retry_suffix))
            err.retry_after = int(retry_after_hdr) if retry_after_hdr and retry_after_hdr.isdigit() else None
            raise err from e
        raise CredentialsError(t("err_api", code=e.code, body=body)) from e

    five_hour = payload.get("five_hour") or {}
    seven_day = payload.get("seven_day") or {}

    limits = {l["kind"]: l for l in payload.get("limits", [])}
    session_active = limits.get("session", {}).get("is_active", True)
    weekly_active = limits.get("weekly_all", {}).get("is_active", True)

    return Usage(
        five_hour=Window(
            percent=float(five_hour.get("utilization") or 0.0),
            resets_at=_parse_dt(five_hour.get("resets_at")),
            active=session_active,
        ),
        seven_day=Window(
            percent=float(seven_day.get("utilization") or 0.0),
            resets_at=_parse_dt(seven_day.get("resets_at")),
            active=weekly_active,
        ),
        plan=plan,
    )


if __name__ == "__main__":
    u = fetch_usage()
    print(f"5h:  {u.five_hour.percent:.0f}%  reset in {u.five_hour.minutes_to_reset} min "
          f"({u.five_hour.resets_at})")
    print(f"7d:  {u.seven_day.percent:.0f}%  reset in {u.seven_day.minutes_to_reset} min "
          f"({u.seven_day.resets_at})")
