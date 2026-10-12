"""Read the plain-text spec format used by the ``typedenv check`` command.

One variable per line: ``NAME TYPE [optional] [secret]``. Blank lines and lines
starting with ``#`` are ignored. TYPE is one of ``str int float bool decimal path
duration json secret``, ``list`` or ``list:SEP`` (items split on SEP, comma by
default), or ``choice:A,B,C`` (exactly one of the listed words).
"""

from __future__ import annotations

from pathlib import Path

from ._check import VarSpec
from ._parsers import parse_list
from ._types import NAMED, Parser, choice_parser, parse_secret

TYPE_HELP = "str, int, float, bool, decimal, path, duration, json, list[:SEP], choice:A,B"
_FLAGS = frozenset({"optional", "secret"})


class SpecError(ValueError):
    """A spec line or a ``--type`` value is malformed."""


def parse_type(token: str) -> tuple[Parser, str]:
    """Return the parser and display name for a type token such as ``list:;``."""
    kind, _, argument = token.partition(":")
    if kind == "list":
        separator = argument or ","
        return (lambda name, raw: parse_list(name, raw, separator)), "list"
    if kind == "choice":
        choices = tuple(word for word in argument.split(",") if word)
        if not choices:
            raise SpecError("choice needs at least one word, for example choice:dev,prod")
        return choice_parser(choices), "choice"
    if not argument and kind in NAMED:
        return NAMED[kind], kind
    raise SpecError(f"unknown type {token!r}; expected one of {TYPE_HELP}")


def parse_spec(text: str, source: str = "spec") -> list[VarSpec]:
    """Turn spec text into variable specs, raising SpecError naming the bad line."""
    specs: list[VarSpec] = []
    for number, line in enumerate(text.splitlines(), start=1):
        words = line.split()
        if not words or words[0].startswith("#"):
            continue
        try:
            specs.append(_line(words))
        except SpecError as exc:
            raise SpecError(f"{source}:{number}: {exc}") from None
    return specs


def _line(words: list[str]) -> VarSpec:
    if len(words) < 2:
        raise SpecError("expected NAME TYPE [optional] [secret]")
    name, token, *flags = words
    unknown = [flag for flag in flags if flag not in _FLAGS]
    if unknown:
        raise SpecError(f"unknown flag {unknown[0]!r}; expected optional or secret")
    parser: Parser
    if token == "secret":
        parser, type_name = parse_secret, "secret"
    else:
        parser, type_name = parse_type(token)
    return VarSpec(
        name=name,
        type_name=type_name,
        parser=parser,
        required="optional" not in flags,
        secret="secret" in flags or token == "secret",
        attr=name,
    )


def read_spec(path: str) -> list[VarSpec]:
    return parse_spec(Path(path).read_text(encoding="utf-8-sig"), path)
