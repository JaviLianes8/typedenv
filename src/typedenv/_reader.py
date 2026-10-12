"""The lookup core shared by every getter: prefix, empty handling, secret masking."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any, TypeVar, cast

from ._errors import InvalidEnvError, MissingEnvError

T = TypeVar("T")
R = TypeVar("R", bound="Reader")


class _Missing:
    """Sentinel telling "no argument given" apart from an explicit None default."""

    def __repr__(self) -> str:
        return "<missing>"


MISSING: Any = _Missing()


class Reader:
    """Look names up in a mapping (``os.environ`` by default) and parse the values.

    ``prefix`` is prepended to every name, so ``Env(prefix="APP_").int("PORT")`` reads
    ``APP_PORT`` and errors name ``APP_PORT``. With ``empty_is_unset=True`` a variable
    set to the empty string counts as unset, which matches how many deployment tools
    write "no value" (``KEY=``).

    Name matching is whatever the mapping does: ``os.environ`` is case-insensitive on
    Windows and case-sensitive on POSIX, while a plain ``dict`` is always exact.
    """

    def __init__(
        self,
        source: Mapping[str, str] | None = None,
        *,
        prefix: str = "",
        empty_is_unset: bool = False,
    ) -> None:
        self._source: Mapping[str, str] = source if source is not None else os.environ
        self.prefix = prefix
        self.empty_is_unset = empty_is_unset

    @property
    def source(self) -> Mapping[str, str]:
        """The mapping values are read from."""
        return self._source

    def prefixed(self: R, prefix: str) -> R:
        """Return a reader over the same source with ``prefix`` appended to the prefix."""
        return type(self)(
            self._source, prefix=self.prefix + prefix, empty_is_unset=self.empty_is_unset
        )

    def full_name(self, name: str) -> str:
        """The real variable name read for ``name``, prefix included."""
        return self.prefix + name

    def raw(self, name: str) -> str | None:
        """Return the unparsed value of ``name``, or None when it is unset."""
        value = self._source.get(self.full_name(name))
        if value is not None and value == "" and self.empty_is_unset:
            return None
        return value

    def is_set(self, name: str) -> bool:
        """Whether ``name`` is set (an empty value counts unless ``empty_is_unset``)."""
        return self.raw(name) is not None

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and self.is_set(name)

    def __repr__(self) -> str:
        where = "os.environ" if self._source is os.environ else type(self._source).__name__
        return (
            f"{type(self).__name__}(source={where}, prefix={self.prefix!r}, "
            f"empty_is_unset={self.empty_is_unset!r})"
        )

    def _get(
        self,
        name: str,
        parser: Callable[[str, str], T],
        default: Any,
        required: Any,
        secret: bool = False,
    ) -> T | None:
        full = self.full_name(name)
        raw = self.raw(name)
        if raw is not None:
            return parse_value(parser, full, raw, secret)
        if required is True:
            raise MissingEnvError(full)
        if default is not MISSING:
            return cast("T | None", default)
        if required is False:
            return None
        raise MissingEnvError(full)


def parse_value(parser: Callable[[str, str], T], name: str, raw: str, secret: bool) -> T:
    """Run ``parser``; for a secret, re-raise outside the handler so no context leaks."""
    if not secret:
        return parser(name, raw)
    failure: InvalidEnvError | None = None
    try:
        return parser(name, raw)
    except InvalidEnvError as exc:
        failure = exc.masked()
    raise failure
