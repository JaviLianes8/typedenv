r"""Read ``.env`` files: a documented subset of python-dotenv 1.x syntax.

Supported, matching ``dotenv_values`` / ``load_dotenv``: blank lines, ``#`` comment
lines, an optional ``export`` keyword, ``KEY=value`` with spaces allowed around ``=``;
unquoted values (trimmed, an inline comment needs whitespace before ``#``); single
quotes (literal, only ``\'`` and ``\\`` are escapes, and ``${`` is refused because
the two references disagree on it); double quotes (escapes
``\\ \' \" \a \b \f \n \r \t \v``); and ``${NAME}`` / ``${NAME:-default}``
expansion in unquoted and double-quoted values. A bare ``KEY`` with no ``=`` is
skipped. Anything else, such as multi-line quoted values or other ``${...}`` forms,
raises :class:`DotenvError` naming the line, instead of being guessed at.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

from ._dotenv_value import Expand, parse_value
from ._errors import DotenvError

_LINE = re.compile(r"\s*(?:export\s+)?(?P<key>[^=#\s'\"]+)\s*(?:=(?P<rest>.*))?")
_WINDOWS_MAX = 32767


def _entries(text: str, path: str | None) -> list[tuple[int, str, str, bool]]:
    """Return ``(line, key, value, expandable)`` for every assignment line."""
    entries = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _LINE.fullmatch(line)
        if match is None:
            raise DotenvError("expected KEY=value", number, path)
        rest = match.group("rest")
        if rest is None:
            continue
        try:
            value, expandable = parse_value(rest)
        except ValueError as exc:
            raise DotenvError(str(exc), number, path) from None
        entries.append((number, match.group("key"), value, expandable))
    return entries


def _resolve(
    text: str, path: str | None, environ: Mapping[str, str], file_first: bool
) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, key, raw, expandable in _entries(text, path):
        lookup = Expand(values, environ, file_first)
        try:
            values[key] = lookup.expand(raw) if expandable else raw
        except ValueError as exc:
            raise DotenvError(str(exc), number, path) from None
    return values


def parse_dotenv(text: str, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Parse ``.env`` text into a dict, like python-dotenv's ``dotenv_values``.

    ``${NAME}`` resolves against earlier keys in the text first, then ``environ``
    (``os.environ`` by default); an unknown name expands to ``""``.
    """
    return _resolve(text, None, os.environ if environ is None else environ, True)


def read_dotenv(
    path: str | os.PathLike[str], environ: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Read and parse a UTF-8 ``.env`` file without touching the environment."""
    text = Path(path).read_text(encoding="utf-8-sig")
    return _resolve(text, os.fspath(path), os.environ if environ is None else environ, True)


def load_dotenv(path: str | os.PathLike[str], *, override: bool = False) -> dict[str, str]:
    """Copy the variables of a ``.env`` file into ``os.environ``; return what was set.

    Like python-dotenv, variables that are already set win unless ``override=True``,
    and the same precedence applies to ``${NAME}`` expansion. On Windows an entry
    whose ``NAME=value`` exceeds 32,767 characters cannot be stored in the process
    environment, so it raises :class:`DotenvError` before anything is written.
    """
    name = os.fspath(path)
    text = Path(path).read_text(encoding="utf-8-sig")
    values = _resolve(text, name, os.environ, override)
    chosen = {k: v for k, v in values.items() if override or k not in os.environ}
    if sys.platform == "win32":
        lines = {key: number for number, key, *_ in _entries(text, name)}
        for key, value in chosen.items():
            if len(key) + 1 + len(value) > _WINDOWS_MAX:
                reason = f"{key} is longer than the 32767 characters Windows allows"
                raise DotenvError(reason, lines[key], name)
    os.environ.update(chosen)
    return chosen


def read_layer(path: str | os.PathLike[str]) -> dict[str, str]:
    """Parse a file the way :func:`load_dotenv` would see it, without writing anything."""
    text = Path(path).read_text(encoding="utf-8-sig")
    return _resolve(text, os.fspath(path), os.environ, False)
