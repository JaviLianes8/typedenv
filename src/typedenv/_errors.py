"""Exceptions raised when an environment variable is missing or malformed."""

from __future__ import annotations


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


class InvalidEnvError(EnvError, ValueError):
    """A variable is set but its value cannot be parsed as the requested type."""

    def __init__(self, name: str, value: str, type_name: str, reason: str = "") -> None:
        self.name = name
        self.value = value
        self.type_name = type_name
        detail = f": {reason}" if reason else ""
        super().__init__(
            f"environment variable {name!r} is not a valid {type_name}: {value!r}{detail}"
        )
