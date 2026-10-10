"""Checks that the overloads give each call the right static return type.

The assertions live in a function that is never called at runtime: ``assert_type``
evaluates its argument, and the required getters raise when a variable is unset.
What matters is that ``mypy src tests`` in the gate verifies the function body, so an
overload that drifts turns the gate red. A small runtime test guards the live path.
"""

from __future__ import annotations

from typing_extensions import assert_type

from typedenv import Env

_env = Env(source={})


def _static_checks() -> None:
    assert_type(_env.str("A"), str)
    assert_type(_env.str("A", "x"), str)
    assert_type(_env.str("A", None), "str | None")
    assert_type(_env.str("A", required=True), str)
    assert_type(_env.str("A", required=False), "str | None")

    assert_type(_env.int("A"), int)
    assert_type(_env.int("A", 1), int)
    assert_type(_env.int("A", None), "int | None")
    assert_type(_env.int("A", required=True), int)
    assert_type(_env.int("A", required=False), "int | None")

    assert_type(_env.float("A"), float)
    assert_type(_env.float("A", None), "float | None")

    assert_type(_env.bool("A"), bool)
    assert_type(_env.bool("A", None), "bool | None")

    assert_type(_env.list("A"), "list[str]")
    assert_type(_env.list("A", None), "list[str] | None")
    assert_type(_env.list("A", required=False), "list[str] | None")


def test_runtime_types_match_the_inferred_types() -> None:
    present = Env(source={"A": "1"})
    assert isinstance(present.int("A"), int)
    assert isinstance(present.str("A"), str)
    assert isinstance(present.list("A"), list)
    assert present.int("MISSING", None) is None
    # Keep the static-only function referenced so linters see it is in use.
    assert callable(_static_checks)
