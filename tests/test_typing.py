"""Checks that the overloads give each call the right static return type.

The assertions live in a function that is never called at runtime: ``assert_type``
evaluates its argument, and the required getters raise when a variable is unset.
What matters is that ``mypy tests`` in the gate verifies the function body, so an
overload that drifts turns the gate red. A small runtime test guards the live path.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from typing_extensions import assert_type

from typedenv import Env, Secret, load

_env = Env(source={})


class Color(enum.Enum):
    RED = "red"


@dataclass(frozen=True)
class _Settings:
    port: int = 80


def _static_checks() -> None:
    assert_type(_env.str("A"), str)
    assert_type(_env.str("A", "x"), str)
    assert_type(_env.str("A", None), "str | None")
    assert_type(_env.str("A", required=True), str)
    assert_type(_env.str("A", required=False), "str | None")
    assert_type(_env.str("A", secret=True), str)

    assert_type(_env.int("A"), int)
    assert_type(_env.int("A", 1), int)
    assert_type(_env.int("A", None), "int | None")
    assert_type(_env.int("A", required=True), int)
    assert_type(_env.int("A", required=False, secret=True), "int | None")

    assert_type(_env.float("A"), float)
    assert_type(_env.float("A", None), "float | None")

    assert_type(_env.bool("A"), bool)
    assert_type(_env.bool("A", None), "bool | None")

    assert_type(_env.list("A"), "list[str]")
    assert_type(_env.list("A", None), "list[str] | None")
    assert_type(_env.list("A", required=False), "list[str] | None")

    assert_type(_env.decimal("A"), Decimal)
    assert_type(_env.decimal("A", Decimal(1)), Decimal)
    assert_type(_env.decimal("A", None), "Decimal | None")
    assert_type(_env.decimal("A", required=False), "Decimal | None")

    assert_type(_env.path("A"), Path)
    assert_type(_env.path("A", None), "Path | None")

    assert_type(_env.duration("A"), timedelta)
    assert_type(_env.duration("A", timedelta()), timedelta)
    assert_type(_env.duration("A", required=False), "timedelta | None")

    assert_type(_env.enum("A", Color), Color)
    assert_type(_env.enum("A", Color, Color.RED), Color)
    assert_type(_env.enum("A", Color, None), "Color | None")
    assert_type(_env.enum("A", Color, required=False), "Color | None")

    assert_type(_env.secret("A"), Secret)
    assert_type(_env.secret("A", None), "Secret | None")
    assert_type(_env.secret("A", required=True), Secret)

    assert_type(_env.prefixed("APP_"), Env)
    assert_type(load(_Settings, _env), _Settings)


def test_runtime_types_match_the_inferred_types() -> None:
    present = Env(source={"A": "1"})
    assert isinstance(present.int("A"), int)
    assert isinstance(present.str("A"), str)
    assert isinstance(present.list("A"), list)
    assert isinstance(present.decimal("A"), Decimal)
    assert isinstance(present.path("A"), Path)
    assert isinstance(present.duration("A"), timedelta)
    assert isinstance(present.secret("A"), Secret)
    assert present.int("MISSING", None) is None
    # Keep the static-only function referenced so linters see it is in use.
    assert callable(_static_checks)
