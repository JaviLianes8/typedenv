"""Pure string-to-value parsers, each raising InvalidEnvError on bad input.

Every parser takes ``(name, raw)`` and keeps its error ``reason`` free of the raw
value, so the caller can mask a secret without the value leaking through the reason.
"""

from __future__ import annotations

import json as _json
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from ._errors import InvalidEnvError

# Same words as the DEFAULT vocabulary of the sibling library boolish, matched after
# trimming and lower-casing.
TRUE_WORDS = frozenset({"1", "true", "yes", "on", "y", "t", "enable", "enabled"})
FALSE_WORDS = frozenset({"0", "false", "no", "off", "n", "f", "disable", "disabled"})

E = TypeVar("E", bound=Enum)


def parse_str(name: str, raw: str) -> str:
    return raw


def parse_int(name: str, raw: str) -> int:
    try:
        return int(raw.strip())
    except ValueError:
        raise InvalidEnvError(name, raw, "integer") from None


def parse_float(name: str, raw: str) -> float:
    try:
        return float(raw.strip())
    except ValueError:
        raise InvalidEnvError(name, raw, "float") from None


def parse_bool(name: str, raw: str) -> bool:
    value = raw.strip().lower()
    if value in TRUE_WORDS:
        return True
    if value in FALSE_WORDS:
        return False
    raise InvalidEnvError(
        name,
        raw,
        "boolean",
        "expected one of true/false, yes/no, on/off, 1/0, enabled/disabled",
    )


def parse_decimal(name: str, raw: str) -> Decimal:
    try:
        value = Decimal(raw.strip())
    except InvalidOperation:
        raise InvalidEnvError(name, raw, "decimal") from None
    if not value.is_finite():
        raise InvalidEnvError(name, raw, "decimal", "must be a finite number")
    return value


def parse_path(name: str, raw: str) -> Path:
    if not raw.strip():
        raise InvalidEnvError(name, raw, "path", "must not be empty")
    return Path(raw)


def split_list(raw: str, separator: str) -> list[str]:
    stripped = raw.strip()
    if not stripped:
        return []
    return [item.strip() for item in stripped.split(separator)]


def parse_list(name: str, raw: str, separator: str) -> list[str]:
    return split_list(raw, separator)


def parse_json(name: str, raw: str) -> Any:
    try:
        return _json.loads(raw)
    except _json.JSONDecodeError as exc:
        reason = f"{exc.msg} at line {exc.lineno} column {exc.colno}"
        raise InvalidEnvError(name, raw, "JSON", reason) from None
    except (ValueError, RecursionError):
        # Integers past the digit limit and pathologically deep nesting land here.
        raise InvalidEnvError(name, raw, "JSON", "too large or too deeply nested") from None


def parse_enum(name: str, raw: str, enum_type: type[E]) -> E:
    """Match a member by name (case-insensitive) first, then by its value as text."""
    value = raw.strip()
    folded = value.casefold()
    for member in enum_type:
        if member.name.casefold() == folded:
            return member
    for member in enum_type:
        if str(member.value) == value:
            return member
    choices = ", ".join(member.name for member in enum_type)
    raise InvalidEnvError(name, raw, enum_type.__name__, f"expected one of {choices}")


def parse_choice(name: str, raw: str, choices: tuple[str, ...]) -> str:
    """Accept one of a fixed set of strings, compared exactly after trimming."""
    value = raw.strip()
    if value in choices:
        return value
    raise InvalidEnvError(name, raw, "choice", f"expected one of {', '.join(choices)}")
