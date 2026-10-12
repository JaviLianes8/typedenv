"""Getters for richer types: Decimal, Path, timedelta, Enum members and secrets."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Literal, TypeVar, overload

from ._duration import parse_duration
from ._parsers import parse_decimal, parse_enum, parse_path, parse_str
from ._reader import MISSING, Reader
from ._secret import Secret

E = TypeVar("E", bound=Enum)


class RichGetters(Reader):
    """Overloaded getters whose return type follows the default and ``required=``."""

    @overload
    def decimal(self, name: str, *, secret: bool = ...) -> Decimal: ...
    @overload
    def decimal(self, name: str, default: Decimal, *, secret: bool = ...) -> Decimal: ...
    @overload
    def decimal(self, name: str, default: None, *, secret: bool = ...) -> Decimal | None: ...
    @overload
    def decimal(self, name: str, *, required: Literal[True], secret: bool = ...) -> Decimal: ...
    @overload
    def decimal(
        self, name: str, *, required: Literal[False], secret: bool = ...
    ) -> Decimal | None: ...
    def decimal(
        self, name: str, default: Any = MISSING, *, required: Any = MISSING, secret: bool = False
    ) -> Decimal | None:
        """Parse an exact decimal such as ``19.99``; NaN and infinities are rejected."""
        return self._get(name, parse_decimal, default, required, secret)

    @overload
    def path(self, name: str, *, secret: bool = ...) -> Path: ...
    @overload
    def path(self, name: str, default: Path, *, secret: bool = ...) -> Path: ...
    @overload
    def path(self, name: str, default: None, *, secret: bool = ...) -> Path | None: ...
    @overload
    def path(self, name: str, *, required: Literal[True], secret: bool = ...) -> Path: ...
    @overload
    def path(self, name: str, *, required: Literal[False], secret: bool = ...) -> Path | None: ...
    def path(
        self, name: str, default: Any = MISSING, *, required: Any = MISSING, secret: bool = False
    ) -> Path | None:
        """Return a ``pathlib.Path``, taken literally (no ``~`` or variable expansion)."""
        return self._get(name, parse_path, default, required, secret)

    @overload
    def duration(self, name: str, *, secret: bool = ...) -> timedelta: ...
    @overload
    def duration(self, name: str, default: timedelta, *, secret: bool = ...) -> timedelta: ...
    @overload
    def duration(self, name: str, default: None, *, secret: bool = ...) -> timedelta | None: ...
    @overload
    def duration(self, name: str, *, required: Literal[True], secret: bool = ...) -> timedelta: ...
    @overload
    def duration(
        self, name: str, *, required: Literal[False], secret: bool = ...
    ) -> timedelta | None: ...
    def duration(
        self, name: str, default: Any = MISSING, *, required: Any = MISSING, secret: bool = False
    ) -> timedelta | None:
        """Parse ``90`` (seconds), ``250ms``, ``1h30m`` or ``1.5h`` into a timedelta."""
        return self._get(name, parse_duration, default, required, secret)

    @overload
    def enum(self, name: str, enum_type: type[E], *, secret: bool = ...) -> E: ...
    @overload
    def enum(self, name: str, enum_type: type[E], default: E, *, secret: bool = ...) -> E: ...
    @overload
    def enum(
        self, name: str, enum_type: type[E], default: None, *, secret: bool = ...
    ) -> E | None: ...
    @overload
    def enum(
        self, name: str, enum_type: type[E], *, required: Literal[True], secret: bool = ...
    ) -> E: ...
    @overload
    def enum(
        self, name: str, enum_type: type[E], *, required: Literal[False], secret: bool = ...
    ) -> E | None: ...
    def enum(
        self,
        name: str,
        enum_type: type[E],
        default: Any = MISSING,
        *,
        required: Any = MISSING,
        secret: bool = False,
    ) -> E | None:
        """Return the member named by the value (any case), or whose value matches it."""
        return self._get(
            name, lambda n, raw: parse_enum(n, raw, enum_type), default, required, secret
        )

    @overload
    def secret(self, name: str) -> Secret: ...
    @overload
    def secret(self, name: str, default: Secret) -> Secret: ...
    @overload
    def secret(self, name: str, default: None) -> Secret | None: ...
    @overload
    def secret(self, name: str, *, required: Literal[True]) -> Secret: ...
    @overload
    def secret(self, name: str, *, required: Literal[False]) -> Secret | None: ...
    def secret(
        self, name: str, default: Any = MISSING, *, required: Any = MISSING
    ) -> Secret | None:
        """Return the value wrapped in :class:`Secret`, which never shows it in a repr."""
        value = self._get(name, parse_str, default, required, True)
        return Secret(value) if isinstance(value, str) else value
