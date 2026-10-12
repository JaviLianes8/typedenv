"""A string wrapper that keeps a sensitive value out of reprs, logs and tracebacks."""

from __future__ import annotations

import hmac
from typing import Any, NoReturn

from ._errors import MASK


class Secret:
    """Hold a sensitive string and only hand it out through :meth:`reveal`.

    ``str()``, ``repr()``, ``format()`` and f-strings all show ``***``, so a settings
    object that holds a ``Secret`` can be printed or logged without leaking it.
    Equality compares the hidden values in constant time. Pickling is refused, so the
    value cannot slip into a cache or a queue by accident.

    >>> token = Secret("hunter2")
    >>> token
    Secret('***')
    >>> token.reveal()
    'hunter2'
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Secret holds a str, not {type(value).__name__}")
        self._value = value

    def reveal(self) -> str:
        """Return the hidden value. Call it only where the value is really needed."""
        return self._value

    def __repr__(self) -> str:
        return f"Secret({MASK!r})"

    def __str__(self) -> str:
        return MASK

    def __format__(self, spec: str) -> str:
        return format(MASK, spec)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Secret):
            return NotImplemented
        return hmac.compare_digest(self._value.encode(), other._value.encode())

    def __hash__(self) -> int:
        return hash((Secret, self._value))

    def __bool__(self) -> bool:
        return bool(self._value)

    def __reduce__(self) -> NoReturn:
        raise TypeError("Secret values cannot be pickled")

    def __copy__(self) -> Secret:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Secret:
        return self
