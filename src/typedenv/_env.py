"""The Env reader: typed getters whose return type mypy infers from the call."""

from __future__ import annotations

from builtins import bool as _bool
from builtins import float as _float
from builtins import int as _int
from builtins import list as _list
from builtins import str as _str
from typing import Any, Literal, overload

from ._parsers import parse_bool, parse_float, parse_int, parse_json, parse_list, parse_str
from ._reader import MISSING
from ._rich import RichGetters

# The getters are named after the builtin types (env.int, env.str, ...), which shadows
# those names inside the class body, so annotations use these module-level aliases.


class Env(RichGetters):
    """Read environment variables as typed values.

    Each getter is overloaded so the static type follows the call: with no default
    and no ``required=`` the result is non-optional and a missing variable raises;
    passing ``None`` or ``required=False`` widens the result to include ``None``.
    ``secret=True`` keeps the value out of any error message.
    """

    @overload
    def str(self, name: _str, *, secret: _bool = ...) -> _str: ...
    @overload
    def str(self, name: _str, default: _str, *, secret: _bool = ...) -> _str: ...
    @overload
    def str(self, name: _str, default: None, *, secret: _bool = ...) -> _str | None: ...
    @overload
    def str(self, name: _str, *, required: Literal[True], secret: _bool = ...) -> _str: ...
    @overload
    def str(self, name: _str, *, required: Literal[False], secret: _bool = ...) -> _str | None: ...
    def str(
        self, name: _str, default: Any = MISSING, *, required: Any = MISSING, secret: _bool = False
    ) -> _str | None:
        """Return the raw value; an empty value is returned as ``""``."""
        return self._get(name, parse_str, default, required, secret)

    @overload
    def int(self, name: _str, *, secret: _bool = ...) -> _int: ...
    @overload
    def int(self, name: _str, default: _int, *, secret: _bool = ...) -> _int: ...
    @overload
    def int(self, name: _str, default: None, *, secret: _bool = ...) -> _int | None: ...
    @overload
    def int(self, name: _str, *, required: Literal[True], secret: _bool = ...) -> _int: ...
    @overload
    def int(self, name: _str, *, required: Literal[False], secret: _bool = ...) -> _int | None: ...
    def int(
        self, name: _str, default: Any = MISSING, *, required: Any = MISSING, secret: _bool = False
    ) -> _int | None:
        """Parse a base-10 integer, ignoring surrounding whitespace."""
        return self._get(name, parse_int, default, required, secret)

    @overload
    def float(self, name: _str, *, secret: _bool = ...) -> _float: ...
    @overload
    def float(self, name: _str, default: _float, *, secret: _bool = ...) -> _float: ...
    @overload
    def float(self, name: _str, default: None, *, secret: _bool = ...) -> _float | None: ...
    @overload
    def float(self, name: _str, *, required: Literal[True], secret: _bool = ...) -> _float: ...
    @overload
    def float(
        self, name: _str, *, required: Literal[False], secret: _bool = ...
    ) -> _float | None: ...
    def float(
        self, name: _str, default: Any = MISSING, *, required: Any = MISSING, secret: _bool = False
    ) -> _float | None:
        """Parse anything Python's ``float()`` accepts, ignoring surrounding whitespace."""
        return self._get(name, parse_float, default, required, secret)

    @overload
    def bool(self, name: _str, *, secret: _bool = ...) -> _bool: ...
    @overload
    def bool(self, name: _str, default: _bool, *, secret: _bool = ...) -> _bool: ...
    @overload
    def bool(self, name: _str, default: None, *, secret: _bool = ...) -> _bool | None: ...
    @overload
    def bool(self, name: _str, *, required: Literal[True], secret: _bool = ...) -> _bool: ...
    @overload
    def bool(
        self, name: _str, *, required: Literal[False], secret: _bool = ...
    ) -> _bool | None: ...
    def bool(
        self, name: _str, default: Any = MISSING, *, required: Any = MISSING, secret: _bool = False
    ) -> _bool | None:
        """Accept true/false, yes/no, on/off, 1/0, y/n, t/f, enable(d)/disable(d), any case."""
        return self._get(name, parse_bool, default, required, secret)

    @overload
    def list(self, name: _str, *, separator: _str = ",", secret: _bool = ...) -> _list[_str]: ...
    @overload
    def list(
        self, name: _str, default: _list[_str], *, separator: _str = ",", secret: _bool = ...
    ) -> _list[_str]: ...
    @overload
    def list(
        self, name: _str, default: None, *, separator: _str = ",", secret: _bool = ...
    ) -> _list[_str] | None: ...
    @overload
    def list(
        self, name: _str, *, required: Literal[True], separator: _str = ",", secret: _bool = ...
    ) -> _list[_str]: ...
    @overload
    def list(
        self, name: _str, *, required: Literal[False], separator: _str = ",", secret: _bool = ...
    ) -> _list[_str] | None: ...
    def list(
        self,
        name: _str,
        default: Any = MISSING,
        *,
        required: Any = MISSING,
        separator: _str = ",",
        secret: _bool = False,
    ) -> _list[_str] | None:
        """Split on ``separator`` and trim each item; an empty value is ``[]``."""
        return self._get(
            name, lambda n, raw: parse_list(n, raw, separator), default, required, secret
        )

    def json(
        self, name: _str, default: Any = MISSING, *, required: Any = MISSING, secret: _bool = False
    ) -> Any:
        """Parse the value as JSON. Return type is Any, so annotate the call site."""
        return self._get(name, parse_json, default, required, secret)


env = Env()
