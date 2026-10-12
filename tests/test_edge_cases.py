"""Edge cases: hostile JSON, typed list items, unresolvable annotations, bad defaults."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from procs import run_cli

from typedenv import Env, EnvValidationError, InvalidEnvError, load, var


@pytest.mark.parametrize("raw", ["1" * 5000, "[" * 100000], ids=["huge-int", "deep-nesting"])
def test_hostile_json_raises_the_library_error(raw: str) -> None:
    with pytest.raises(InvalidEnvError) as info:
        Env({"X": raw}).json("X", secret=True)
    assert info.value.type_name == "JSON"
    assert raw[:20] not in str(info.value)


def test_hostile_json_is_collected_by_load() -> None:
    @dataclass
    class Conf:
        limits: dict[str, int]
        port: int

    with pytest.raises(EnvValidationError) as info:
        load(Conf, Env({"LIMITS": "[" * 100000}))
    assert [error.name for error in info.value.errors] == ["LIMITS", "PORT"]


def test_typed_list_errors_name_the_item_without_quoting_it() -> None:
    @dataclass
    class Nums:
        values: list[int] = var(default_factory=list, secret=True)

    with pytest.raises(EnvValidationError) as info:
        load(Nums, Env({"VALUES": "1,hunter2,3"}))
    message = str(info.value)
    assert "item 2 is not a valid integer" in message
    assert "hunter2" not in message


def test_empty_list_item_reports_its_position() -> None:
    @dataclass
    class Nums:
        values: list[int]

    with pytest.raises(EnvValidationError) as info:
        load(Nums, Env({"VALUES": "1,,2"}))
    assert "not a valid list" in str(info.value)
    assert "item 2" in str(info.value)


def test_unresolvable_annotations_raise_type_error() -> None:
    @dataclass
    class Local:
        value: Undefined  # type: ignore[name-defined]  # noqa: F821

    with pytest.raises(TypeError) as info:
        load(Local, Env({"VALUE": "x"}))
    assert "Local" in str(info.value)


def test_cli_blames_a_bad_default_not_the_variable() -> None:
    result = run_cli({}, "get", "PORT", "--type", "int", "--default", "abc")
    assert result.returncode == 1
    assert "--default for PORT" in result.stderr


def test_cli_reports_hostile_json_cleanly() -> None:
    result = run_cli({"C": "[" * 100000}, "get", "C", "--type", "json")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "too large or too deeply nested" in result.stderr
