"""Exceptions raised when an environment variable is missing or malformed."""

from __future__ import annotations

from collections.abc import Iterable

MASK = "***"
"""What a secret value is replaced with in every message and attribute."""

_SHOWN = 80


def _shown(value: str) -> str:
    """Quote a value for a message, trimming very long ones to stay readable."""
    if len(value) <= _SHOWN:
        return repr(value)
    return f"{value[:_SHOWN]!r}... ({len(value)} characters)"


class EnvError(Exception):
    """Base class for every error raised by this package."""


class MissingEnvError(EnvError, KeyError):
    """A required variable is not set and no default was given.

    Subclasses KeyError so existing ``except KeyError`` handlers keep working.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        # KeyError.__str__ quotes its argument, so build the message on Exception.
        Exception.__init__(self, f"required environment variable {name!r} is not set")

    def __str__(self) -> str:
        return str(self.args[0])


class InvalidEnvError(EnvError, ValueError):
    """A variable is set but its value cannot be parsed as the requested type.

    With ``secret=True`` the value never reaches the message or the ``value``
    attribute: both carry ``"***"`` instead, and ``reason`` must not quote it either.
    """

    def __init__(
        self,
        name: str,
        value: str,
        type_name: str,
        reason: str = "",
        *,
        secret: bool = False,
    ) -> None:
        self.name = name
        self.value = MASK if secret else value
        self.type_name = type_name
        self.reason = reason
        self.secret = secret
        shown = MASK if secret else _shown(value)
        suffix = f": {reason}" if reason else ""
        # The message without the variable name, for reports that already show it.
        self.detail = f"not a valid {type_name}: {shown}{suffix}"
        super().__init__(f"environment variable {name!r} is {self.detail}")

    def masked(self) -> InvalidEnvError:
        """Return a copy of this error that hides the value."""
        return InvalidEnvError(self.name, MASK, self.type_name, self.reason, secret=True)


class EnvValidationError(EnvError, ValueError):
    """Several variables failed at once; ``errors`` holds every one of them.

    Raised by :func:`typedenv.load` after it has read every field, so a single run
    reports all missing and invalid variables instead of stopping at the first.
    """

    def __init__(self, errors: Iterable[MissingEnvError | InvalidEnvError]) -> None:
        self.errors: tuple[MissingEnvError | InvalidEnvError, ...] = tuple(errors)
        count = len(self.errors)
        noun = "variable" if count == 1 else "variables"
        lines = [f"{count} environment {noun} failed validation:"]
        lines.extend(f"  - {error}" for error in self.errors)
        super().__init__("\n".join(lines))


class DotenvError(EnvError, ValueError):
    """A ``.env`` file uses syntax outside the supported subset.

    The message names the file and line but never quotes the offending value.
    """

    def __init__(self, reason: str, line: int, path: str | None = None) -> None:
        self.reason = reason
        self.line = line
        self.path = path
        where = f"{path}:{line}" if path else f"line {line}"
        super().__init__(f"{where}: {reason}")
