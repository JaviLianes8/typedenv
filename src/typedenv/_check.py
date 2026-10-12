"""Evaluate a list of variable specs against a reader, collecting every outcome."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from ._errors import InvalidEnvError, MissingEnvError
from ._reader import MISSING, Reader, parse_value


@dataclass(frozen=True)
class VarSpec:
    """One variable to read: its name, parser and what to do when it is unset."""

    name: str
    type_name: str
    parser: Callable[[str, str], Any]
    required: bool = True
    default: Any = MISSING
    default_factory: Callable[[], Any] | None = None
    secret: bool = False
    attr: str = ""

    def fallback(self) -> Any:
        """The value used when the variable is unset and not required."""
        if self.default_factory is not None:
            return self.default_factory()
        return None if self.default is MISSING else self.default


@dataclass(frozen=True)
class Outcome:
    """The result of reading one spec.

    ``status`` is ``"ok"`` (set and valid), ``"unset"`` (unset but optional, so
    ``value`` is the fallback), ``"missing"`` or ``"invalid"`` (``error`` is set).
    """

    spec: VarSpec
    full_name: str
    status: str
    value: Any = None
    error: MissingEnvError | InvalidEnvError | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None


def evaluate_one(spec: VarSpec, reader: Reader) -> Outcome:
    full = reader.full_name(spec.name)
    raw = reader.raw(spec.name)
    if raw is None:
        if spec.required:
            return Outcome(spec, full, "missing", error=MissingEnvError(full))
        return Outcome(spec, full, "unset", spec.fallback())
    try:
        value = parse_value(spec.parser, full, raw, spec.secret)
    except InvalidEnvError as exc:
        return Outcome(spec, full, "invalid", error=exc)
    return Outcome(spec, full, "ok", value)


def evaluate(specs: Iterable[VarSpec], reader: Reader) -> list[Outcome]:
    """Read every spec, never stopping at the first failure."""
    return [evaluate_one(spec, reader) for spec in specs]
