"""Decode the value part of one ``.env`` line and expand ``${NAME}`` references."""

from __future__ import annotations

import re
from collections.abc import Mapping

_SINGLE = re.compile(r"'((?:\\'|[^'])*)'")
_DOUBLE = re.compile(r'"((?:\\"|[^"])*)"')
_TAIL = re.compile(r"\s*(?:#.*)?")
_SINGLE_ESCAPES = re.compile(r"\\([\\'])")
_DOUBLE_ESCAPES = re.compile(r"\\([\\'\"abfnrtv])")
_CONTROL = {"a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
_REFERENCE = re.compile(r"\$\{([^}]*)\}")
_PLAIN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?")
# python-dotenv 1.x expands ${...} inside single quotes while docker compose keeps it
# literal, so the subset refuses the construct rather than pick one silently.
_AMBIGUOUS = "${ inside single quotes is read differently by python-dotenv and docker compose"


def parse_value(rest: str) -> tuple[str, bool]:
    """Return ``(value, expandable)`` for the text after ``=``.

    Raises ValueError with a reason that never quotes the value.
    """
    text = rest.lstrip()
    if text.startswith(("'", '"')):
        quote = text[0]
        match = (_SINGLE if quote == "'" else _DOUBLE).match(text)
        if match is None:
            raise ValueError("unterminated quoted value (multi-line values are not supported)")
        if _TAIL.fullmatch(text, match.end()) is None:
            raise ValueError("unexpected text after the closing quote")
        body = match.group(1)
        if quote == "'":
            if "${" in body:
                raise ValueError(_AMBIGUOUS)
            return _SINGLE_ESCAPES.sub(r"\1", body), False
        return _DOUBLE_ESCAPES.sub(lambda m: _CONTROL.get(m.group(1), m.group(1)), body), True
    return re.sub(r"\s+#.*", "", text).rstrip(), True


class Expand:
    """Resolve ``${NAME}`` and ``${NAME:-default}`` against the file and an environment.

    ``file_first`` decides who wins when a name exists in both: the earlier file
    entries (``dotenv_values`` behaviour) or the environment (``load_dotenv`` without
    ``override``). An unknown name with no default expands to ``""``; the default is
    used only when the name is unset, never when it is set to ``""``.
    """

    def __init__(self, values: Mapping[str, str], environ: Mapping[str, str], file_first: bool):
        self._first, self._second = (values, environ) if file_first else (environ, values)

    def lookup(self, name: str) -> str | None:
        value = self._first.get(name)
        return value if value is not None else self._second.get(name)

    def expand(self, raw: str) -> str:
        if "${" not in raw:
            return raw
        if raw.count("${") != len(_REFERENCE.findall(raw)):
            raise ValueError("unterminated ${ reference")
        return _REFERENCE.sub(self._replace, raw)

    def _replace(self, match: re.Match[str]) -> str:
        inner = _PLAIN.fullmatch(match.group(1))
        if inner is None:
            raise ValueError("only ${NAME} and ${NAME:-default} references are supported")
        value = self.lookup(inner.group(1))
        if value is not None:
            return value
        return inner.group(2) or ""
