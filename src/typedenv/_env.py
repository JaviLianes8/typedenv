"""The Env reader: typed getters whose return type mypy infers from the call."""

from __future__ import annotations

import os
from builtins import bool as _bool
from builtins import float as _float
from builtins import int as _int
from builtins import list as _list
from builtins import str as _str
from collections.abc import Callable, Mapping
from typing import Any, Literal, TypeVar, cast, overload

from ._errors import MissingEnvError
from ._parsers import parse_bool, parse_float, parse_int, parse_json, parse_list

# The getters are named after the builtin types (env.int, env.str, ...), which shadows
# those names inside the class body, so annotations use these module-level aliases.

T = TypeVar("T")


class _Missing:
    """Sentinel telling "no argument given" apart from an explicit None default."""


_MISSING = _Missing()


def _identity(name: _str, raw: _str) -> _str:
    return raw


class Env:
    """Read environment variables as typed values.

    Each getter is overloaded so the static type follows the call: with no default
    and no ``required=`` the result is non-optional and a missing variable raises;
    passing ``None`` or ``required=False`` widens the result to include ``None``.
    """

    def __init__(self, source: Mapping[_str, _str] | None = None) -> None:
        self._source = source if source is not None else os.environ

    def _get(
        self,
        name: _str,
        parser: Callable[[_str, _str], T],
        default: Any,
        required: Any,
    ) -> T | None:
        raw = self._source.get(name)
        if raw is not None:
            return parser(name, raw)
        if required is True:
            raise MissingEnvError(name)
        if default is not _MISSING:
            return cast("T | None", default)
        if required is False:
            return None
        raise MissingEnvError(name)

    @overload
    def str(self, name: _str) -> _str: ...
    @overload
    def str(self, name: _str, default: _str) -> _str: ...
    @overload
    def str(self, name: _str, default: None) -> _str | None: ...
    @overload
    def str(self, name: _str, *, required: Literal[True]) -> _str: ...
    @overload
    def str(self, name: _str, *, required: Literal[False]) -> _str | None: ...
    def str(self, name: _str, default: Any = _MISSING, *, required: Any = _MISSING) -> _str | None:
        return self._get(name, _identity, default, required)

    @overload
    def int(self, name: _str) -> _int: ...
    @overload
    def int(self, name: _str, default: _int) -> _int: ...
    @overload
    def int(self, name: _str, default: None) -> _int | None: ...
    @overload
    def int(self, name: _str, *, required: Literal[True]) -> _int: ...
    @overload
    def int(self, name: _str, *, required: Literal[False]) -> _int | None: ...
    def int(self, name: _str, default: Any = _MISSING, *, required: Any = _MISSING) -> _int | None:
        return self._get(name, parse_int, default, required)

    @overload
    def float(self, name: _str) -> _float: ...
    @overload
    def float(self, name: _str, default: _float) -> _float: ...
    @overload
    def float(self, name: _str, default: None) -> _float | None: ...
    @overload
    def float(self, name: _str, *, required: Literal[True]) -> _float: ...
    @overload
    def float(self, name: _str, *, required: Literal[False]) -> _float | None: ...
    def float(
        self, name: _str, default: Any = _MISSING, *, required: Any = _MISSING
    ) -> _float | None:
        return self._get(name, parse_float, default, required)

    @overload
    def bool(self, name: _str) -> _bool: ...
    @overload
    def bool(self, name: _str, default: _bool) -> _bool: ...
    @overload
    def bool(self, name: _str, default: None) -> _bool | None: ...
    @overload
    def bool(self, name: _str, *, required: Literal[True]) -> _bool: ...
    @overload
    def bool(self, name: _str, *, required: Literal[False]) -> _bool | None: ...
    def bool(
        self, name: _str, default: Any = _MISSING, *, required: Any = _MISSING
    ) -> _bool | None:
        return self._get(name, parse_bool, default, required)

    @overload
    def list(self, name: _str, *, separator: _str = ",") -> _list[_str]: ...
    @overload
    def list(self, name: _str, default: _list[_str], *, separator: _str = ",") -> _list[_str]: ...
    @overload
    def list(self, name: _str, default: None, *, separator: _str = ",") -> _list[_str] | None: ...
    @overload
    def list(
        self, name: _str, *, required: Literal[True], separator: _str = ","
    ) -> _list[_str]: ...
    @overload
    def list(
        self, name: _str, *, required: Literal[False], separator: _str = ","
    ) -> _list[_str] | None: ...
    def list(
        self,
        name: _str,
        default: Any = _MISSING,
        *,
        required: Any = _MISSING,
        separator: _str = ",",
    ) -> _list[_str] | None:
        return self._get(name, lambda n, raw: parse_list(n, raw, separator), default, required)

    def json(self, name: _str, default: Any = _MISSING, *, required: Any = _MISSING) -> Any:
        """Parse the value as JSON. Return type is Any, so annotate the call site."""
        return self._get(name, parse_json, default, required)


env = Env()
