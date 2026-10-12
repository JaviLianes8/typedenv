"""Populate a plain dataclass from the environment, reporting every failure at once."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any, TypeVar, get_type_hints

from ._check import VarSpec, evaluate
from ._env import Env, env
from ._errors import EnvValidationError
from ._reader import MISSING
from ._secret import Secret
from ._types import resolve, unwrap_optional

T = TypeVar("T")
_KEY = "typedenv"


@dataclasses.dataclass(frozen=True)
class _VarOptions:
    name: str | None
    separator: str
    secret: bool


def var(
    name: str | None = None,
    *,
    default: Any = MISSING,
    default_factory: Callable[[], Any] | None = None,
    separator: str = ",",
    secret: bool = False,
) -> Any:
    """Describe how a dataclass field is read; use it where you would use ``field()``.

    ``name`` overrides the variable name (the field name upper-cased by default; any
    prefix still applies). ``default`` / ``default_factory`` make the field optional,
    ``separator`` splits ``list[...]`` and ``tuple[..., ...]`` fields, and ``secret``
    keeps the value out of error messages.
    """
    if default is not MISSING and default_factory is not None:
        raise ValueError("pass default or default_factory, not both")
    metadata = {_KEY: _VarOptions(name, separator, secret)}
    if default_factory is not None:
        return dataclasses.field(default_factory=default_factory, metadata=metadata)
    if default is not MISSING:
        return dataclasses.field(default=default, metadata=metadata)
    return dataclasses.field(metadata=metadata)


def specs_for(cls: type[Any]) -> list[VarSpec]:
    """Build one spec per init field of the dataclass ``cls``."""
    if not (isinstance(cls, type) and dataclasses.is_dataclass(cls)):
        raise TypeError(f"expected a dataclass type, got {cls!r}")
    try:
        hints = get_type_hints(cls)
    except NameError as exc:
        raise TypeError(f"cannot resolve the annotations of {cls.__qualname__}: {exc}") from None
    return [_spec(field, hints[field.name]) for field in dataclasses.fields(cls) if field.init]


def _spec(field: dataclasses.Field[Any], annotation: Any) -> VarSpec:
    options = field.metadata.get(_KEY) or _VarOptions(None, ",", False)
    inner, optional = unwrap_optional(annotation)
    parser, type_name = resolve(inner, options.separator)
    has_default = field.default is not dataclasses.MISSING
    factory = field.default_factory
    has_factory = factory is not dataclasses.MISSING
    return VarSpec(
        name=options.name or field.name.upper(),
        type_name=type_name,
        parser=parser,
        required=not (has_default or has_factory or optional),
        default=field.default if has_default else MISSING,
        default_factory=factory if has_factory else None,  # type: ignore[arg-type]
        secret=options.secret or inner is Secret,
        attr=field.name,
    )


def load(cls: type[T], source: Env | None = None) -> T:
    """Read every field of the dataclass ``cls`` from the environment and build it.

    Each field is read from the upper-cased field name (or ``var(name=...)``), with
    the prefix of ``source`` applied (``Env(prefix="APP_")``). A field with a default,
    a ``default_factory`` or an ``X | None`` annotation is optional; any other field
    is required. Every field is read before anything is raised, so one
    :class:`EnvValidationError` lists all missing and invalid variables together.
    """
    outcomes = evaluate(specs_for(cls), source if source is not None else env)
    errors = [outcome.error for outcome in outcomes if outcome.error is not None]
    if errors:
        raise EnvValidationError(errors)
    return cls(**{outcome.spec.attr: outcome.value for outcome in outcomes})
