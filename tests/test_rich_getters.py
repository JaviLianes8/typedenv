"""Behaviour tests for the getters added in 0.2: decimal, path, duration, enum, secret."""

from __future__ import annotations

import enum
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from typedenv import Env, InvalidEnvError, MissingEnvError, Secret


class Level(enum.Enum):
    DEBUG = 10
    INFO = 20


class Mode(enum.Enum):
    DEV = "dev"
    PROD = "prod"


def make_env(**values: str) -> Env:
    return Env(source=dict(values))


def test_decimal_is_exact() -> None:
    assert make_env(PRICE=" 19.99 ").decimal("PRICE") == Decimal("19.99")


@pytest.mark.parametrize("raw", ["NaN", "sNaN", "Infinity", "-inf", "abc", ""])
def test_decimal_rejects_non_finite_and_garbage(raw: str) -> None:
    with pytest.raises(InvalidEnvError) as info:
        make_env(PRICE=raw).decimal("PRICE")
    assert info.value.type_name == "decimal"


def test_decimal_default_and_optional() -> None:
    assert make_env().decimal("PRICE", Decimal("1")) == Decimal("1")
    assert make_env().decimal("PRICE", None) is None
    with pytest.raises(MissingEnvError):
        make_env().decimal("PRICE")


def test_path_is_taken_literally() -> None:
    assert make_env(DATA="~/data").path("DATA") == Path("~/data")


def test_path_rejects_an_empty_value() -> None:
    with pytest.raises(InvalidEnvError):
        make_env(DATA="  ").path("DATA")


def test_path_default_and_required_false() -> None:
    assert make_env().path("DATA", Path("x")) == Path("x")
    assert make_env().path("DATA", required=False) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("90", timedelta(seconds=90)),
        ("1.5", timedelta(seconds=1.5)),
        ("250ms", timedelta(milliseconds=250)),
        ("1h30m", timedelta(hours=1, minutes=30)),
        ("1.5h", timedelta(minutes=90)),
        ("2d", timedelta(days=2)),
        (
            "1w2d3h4m5s6ms",
            timedelta(weeks=1, days=2, hours=3, minutes=4, seconds=5, milliseconds=6),
        ),
        (" 5M ", timedelta(minutes=5)),
        ("0", timedelta(0)),
    ],
)
def test_duration_accepts_seconds_and_units(raw: str, expected: timedelta) -> None:
    assert make_env(T=raw).duration("T") == expected


@pytest.mark.parametrize(
    "raw", ["", "-5", "5x", "30m1h", "1h1h", "1 h", "h", "1e3", "inf", "1h 30m"]
)
def test_duration_rejects_malformed_values(raw: str) -> None:
    with pytest.raises(InvalidEnvError) as info:
        make_env(T=raw).duration("T")
    assert info.value.type_name == "duration"


def test_duration_rejects_overflow() -> None:
    with pytest.raises(InvalidEnvError):
        make_env(T="9" * 30 + "w").duration("T")


def test_enum_matches_name_in_any_case_then_value() -> None:
    assert make_env(L="debug").enum("L", Level) is Level.DEBUG
    assert make_env(L="20").enum("L", Level) is Level.INFO
    assert make_env(M="prod").enum("M", Mode) is Mode.PROD


def test_enum_error_lists_the_choices() -> None:
    with pytest.raises(InvalidEnvError) as info:
        make_env(L="loud").enum("L", Level)
    assert "DEBUG, INFO" in str(info.value)
    assert info.value.type_name == "Level"


def test_enum_default_and_optional() -> None:
    assert make_env().enum("L", Level, Level.INFO) is Level.INFO
    assert make_env().enum("L", Level, None) is None


def test_secret_wraps_the_value() -> None:
    token = make_env(TOKEN="hunter2").secret("TOKEN")
    assert isinstance(token, Secret)
    assert token.reveal() == "hunter2"
    assert "hunter2" not in repr(token)


def test_secret_default_and_optional() -> None:
    assert make_env().secret("TOKEN", Secret("d")) == Secret("d")
    assert make_env().secret("TOKEN", None) is None
    assert make_env().secret("TOKEN", required=False) is None
    with pytest.raises(MissingEnvError):
        make_env().secret("TOKEN", required=True)


SECRET_CALLS = [
    lambda e: e.int("X", secret=True),
    lambda e: e.float("X", secret=True),
    lambda e: e.bool("X", secret=True),
    lambda e: e.json("X", secret=True),
    lambda e: e.decimal("X", secret=True),
    lambda e: e.duration("X", secret=True),
    lambda e: e.enum("X", Level, secret=True),
]


@pytest.mark.parametrize("call", SECRET_CALLS)
def test_secret_flag_keeps_the_value_out_of_the_error(call: object) -> None:
    value = "s3cr3t-value-{not json"
    with pytest.raises(InvalidEnvError) as info:
        call(make_env(X=value))  # type: ignore[operator]
    error = info.value
    assert value not in str(error)
    assert value not in repr(error)
    assert error.value == "***"
    assert error.secret is True
    assert error.__cause__ is None
    assert error.__context__ is None
    assert "X" in str(error)


def test_long_values_are_trimmed_in_messages_but_kept_whole() -> None:
    value = "x" * 500
    with pytest.raises(InvalidEnvError) as info:
        make_env(N=value).int("N")
    assert len(str(info.value)) < 250
    assert "500 characters" in str(info.value)
    assert info.value.value == value
