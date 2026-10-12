"""Parse human durations such as ``90``, ``250ms``, ``1h30m`` or ``1.5h``."""

from __future__ import annotations

import re
from datetime import timedelta

from ._errors import InvalidEnvError

_UNITS = {
    "ms": 0.001,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "w": 604800.0,
}
_PART = re.compile(r"(\d+(?:\.\d+)?|\.\d+)(ms|s|m|h|d|w)")
_REASON = "expected seconds (90) or amounts with units ms, s, m, h, d, w (1h30m, 250ms)"


def parse_duration(name: str, raw: str) -> timedelta:
    """Return a non-negative timedelta.

    A bare number is seconds. Otherwise the value is one or more ``<number><unit>``
    parts with no spaces between them, each unit used at most once and from the
    largest to the smallest, so ``1h30m`` is valid and ``30m1h`` is not.
    """
    text = raw.strip().lower()
    try:
        return timedelta(seconds=float(text)) if _is_number(text) else _parse_parts(text)
    except (ValueError, OverflowError):
        raise InvalidEnvError(name, raw, "duration", _REASON) from None


def _is_number(text: str) -> bool:
    return re.fullmatch(r"\d+(?:\.\d+)?|\.\d+", text) is not None


def _parse_parts(text: str) -> timedelta:
    if not text:
        raise ValueError("empty")
    order = list(_UNITS)[::-1]
    position = 0
    last_rank = -1
    seconds = 0.0
    while position < len(text):
        match = _PART.match(text, position)
        if match is None:
            raise ValueError("bad part")
        rank = order.index(match.group(2))
        if rank <= last_rank:
            raise ValueError("units out of order")
        last_rank = rank
        seconds += float(match.group(1)) * _UNITS[match.group(2)]
        position = match.end()
    return timedelta(seconds=seconds)
