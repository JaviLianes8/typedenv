"""Pure string-to-value parsers, each raising InvalidEnvError on bad input."""

from __future__ import annotations

import json as _json
from typing import Any

from ._errors import InvalidEnvError

_TRUE = frozenset({"1", "true", "yes", "on", "y", "t"})
_FALSE = frozenset({"0", "false", "no", "off", "n", "f"})


def parse_int(name: str, raw: str) -> int:
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise InvalidEnvError(name, raw, "integer") from exc


def parse_float(name: str, raw: str) -> float:
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise InvalidEnvError(name, raw, "float") from exc


def parse_bool(name: str, raw: str) -> bool:
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise InvalidEnvError(
        name,
        raw,
        "boolean",
        "expected one of true/false, yes/no, on/off, 1/0",
    )


def parse_list(name: str, raw: str, separator: str) -> list[str]:
    stripped = raw.strip()
    if not stripped:
        return []
    return [item.strip() for item in stripped.split(separator)]


def parse_json(name: str, raw: str) -> Any:
    try:
        return _json.loads(raw)
    except _json.JSONDecodeError as exc:
        raise InvalidEnvError(name, raw, "JSON", exc.msg) from exc
