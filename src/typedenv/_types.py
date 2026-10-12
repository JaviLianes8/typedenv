"""Map a type annotation, or a type name from a spec file, to a parser."""

from __future__ import annotations

import types
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin

from ._duration import parse_duration
from ._errors import InvalidEnvError
from ._parsers import (
    parse_bool,
    parse_choice,
    parse_decimal,
    parse_enum,
    parse_float,
    parse_int,
    parse_json,
    parse_path,
    parse_str,
    split_list,
)
from ._secret import Secret

Parser = Callable[[str, str], Any]

SCALARS: dict[Any, tuple[Parser, str]] = {
    str: (parse_str, "str"),
    int: (parse_int, "int"),
    float: (parse_float, "float"),
    bool: (parse_bool, "bool"),
    Decimal: (parse_decimal, "decimal"),
    Path: (parse_path, "path"),
    timedelta: (parse_duration, "duration"),
}

NAMED: dict[str, Parser] = {name: parser for parser, name in SCALARS.values()}
NAMED["json"] = parse_json


def parse_secret(name: str, raw: str) -> Secret:
    return Secret(raw)


def split_parser(item: Parser, separator: str, kind: Callable[[list[Any]], Any]) -> Parser:
    """Build a parser that splits on ``separator`` and parses every item."""

    def parse(name: str, raw: str) -> Any:
        return kind([item(name, part) for part in split_list(raw, separator)])

    return parse


def choice_parser(choices: tuple[str, ...]) -> Parser:
    return lambda name, raw: parse_choice(name, raw, choices)


def _json_object(name: str, raw: str) -> dict[str, Any]:
    value = parse_json(name, raw)
    if not isinstance(value, dict):
        raise InvalidEnvError(name, raw, "JSON object", "expected a JSON object")
    return value


def unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """Return ``(inner, True)`` for ``X | None`` / ``Optional[X]``, else ``(annotation, False)``."""
    if get_origin(annotation) in (Union, types.UnionType):
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1 and len(args) < len(get_args(annotation)):
            return args[0], True
    return annotation, False


def resolve(annotation: Any, separator: str) -> tuple[Parser, str]:
    """Return the parser and a readable type name for a field annotation.

    Raises TypeError for an annotation this package cannot read from a string.
    """
    if annotation in SCALARS:
        return SCALARS[annotation]
    if annotation is Secret:
        return parse_secret, "secret"
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        enum_type = annotation
        return (lambda name, raw: parse_enum(name, raw, enum_type)), enum_type.__name__
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Literal and args and all(isinstance(arg, str) for arg in args):
        return choice_parser(tuple(args)), "choice"
    if origin is dict or annotation is dict:
        return _json_object, "JSON object"
    if origin in (list, tuple) and args:
        homogeneous = origin is list or (len(args) == 2 and args[1] is Ellipsis)
        if homogeneous and args[0] in SCALARS:
            item, item_name = SCALARS[args[0]]
            kind: Callable[[list[Any]], Any] = list if origin is list else tuple
            return split_parser(item, separator, kind), f"{origin.__name__}[{item_name}]"
    raise TypeError(f"typedenv cannot read a field annotated {annotation!r} from a string")
