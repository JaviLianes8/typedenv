"""Render check outcomes as an aligned text table or as JSON, never leaking secrets."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from ._check import Outcome
from ._errors import MASK, InvalidEnvError
from ._secret import Secret


def canonical(value: Any) -> str:
    """Format a parsed value the way the command line prints it."""
    if isinstance(value, Secret):
        return MASK
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, timedelta):
        seconds = value.total_seconds()
        return str(int(seconds)) if seconds.is_integer() else str(seconds)
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, (Decimal, Path, int, float, str)):
        return str(value)
    if value is None:
        return ""
    return json.dumps(value, default=canonical, ensure_ascii=False)


def _shown(outcome: Outcome) -> str:
    if outcome.spec.secret:
        return MASK
    return canonical(outcome.value) if outcome.status in ("ok", "unset") else ""


def _detail(outcome: Outcome, show_values: bool) -> str:
    kind = outcome.spec.type_name + ("" if outcome.spec.required else ", optional")
    if outcome.spec.secret and outcome.spec.type_name != "secret":
        kind += ", secret"
    if isinstance(outcome.error, InvalidEnvError):
        return f"{kind}: {outcome.error.detail}"
    if outcome.status == "missing":
        return f"{kind}: not set"
    if show_values and (outcome.status == "ok" or outcome.value is not None):
        return f"{kind} = {_shown(outcome)}"
    return kind


def render_text(outcomes: Sequence[Outcome], show_values: bool) -> str:
    width = max((len(outcome.full_name) for outcome in outcomes), default=0)
    lines = [
        f"{outcome.status:<8} {outcome.full_name:<{width}}  {_detail(outcome, show_values)}"
        for outcome in outcomes
    ]
    return "\n".join(lines)


def render_json(outcomes: Sequence[Outcome], show_values: bool) -> str:
    rows = []
    for outcome in outcomes:
        row: dict[str, Any] = {
            "name": outcome.full_name,
            "type": outcome.spec.type_name,
            "status": outcome.status,
            "required": outcome.spec.required,
            "secret": outcome.spec.secret,
            "error": None if outcome.error is None else str(outcome.error),
        }
        if show_values and outcome.status in ("ok", "unset"):
            row["value"] = _shown(outcome)
        rows.append(row)
    ok = not any(outcome.failed for outcome in outcomes)
    return json.dumps({"ok": ok, "variables": rows}, indent=2, ensure_ascii=False)


def summary(outcomes: Sequence[Outcome]) -> str:
    failed = sum(1 for outcome in outcomes if outcome.failed)
    total = len(outcomes)
    noun = "variable" if total == 1 else "variables"
    if failed:
        return f"{failed} of {total} {noun} failed"
    return f"all {total} {noun} ok"
