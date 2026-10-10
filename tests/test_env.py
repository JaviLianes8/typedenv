"""Behaviour tests for the Env getters, including the failure paths."""

from __future__ import annotations

import pytest

from typedenv import Env, InvalidEnvError, MissingEnvError


def make_env(**values: str) -> Env:
    return Env(source=dict(values))


def test_str_returns_the_raw_value() -> None:
    assert make_env(NAME="ada").str("NAME") == "ada"


def test_int_parses_a_decimal() -> None:
    assert make_env(PORT="8080").int("PORT") == 8080


def test_int_parses_a_negative_value() -> None:
    assert make_env(OFFSET="-5").int("OFFSET") == -5


def test_float_parses_a_decimal() -> None:
    assert make_env(RATE="0.25").float("RATE") == 0.25


@pytest.mark.parametrize("raw", ["true", "Yes", "ON", "1", "t", "y"])
def test_bool_accepts_truthy_spellings(raw: str) -> None:
    assert make_env(FLAG=raw).bool("FLAG") is True


@pytest.mark.parametrize("raw", ["false", "No", "OFF", "0", "f", "n"])
def test_bool_accepts_falsy_spellings(raw: str) -> None:
    assert make_env(FLAG=raw).bool("FLAG") is False


def test_list_splits_on_the_default_separator() -> None:
    assert make_env(HOSTS="a, b ,c").list("HOSTS") == ["a", "b", "c"]


def test_list_honours_a_custom_separator() -> None:
    assert make_env(PATHS="a;b;c").list("PATHS", separator=";") == ["a", "b", "c"]


def test_list_of_an_empty_value_is_empty() -> None:
    assert make_env(HOSTS="").list("HOSTS") == []


def test_json_parses_an_object() -> None:
    assert make_env(CONF='{"a": 1}').json("CONF") == {"a": 1}


def test_default_is_used_when_the_variable_is_unset() -> None:
    assert make_env().int("PORT", 80) == 80


def test_a_set_value_wins_over_the_default() -> None:
    assert make_env(PORT="9090").int("PORT", 80) == 9090


def test_none_default_makes_a_missing_variable_return_none() -> None:
    assert make_env().int("PORT", None) is None


def test_required_false_returns_none_when_unset() -> None:
    assert make_env().str("TOKEN", required=False) is None


def test_missing_required_variable_raises_naming_it() -> None:
    with pytest.raises(MissingEnvError) as info:
        make_env().int("PORT")
    assert "PORT" in str(info.value)


def test_required_true_raises_when_unset() -> None:
    with pytest.raises(MissingEnvError):
        make_env().str("TOKEN", required=True)


def test_missing_env_error_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        make_env().int("PORT")


def test_bad_int_raises_naming_the_variable_and_value() -> None:
    with pytest.raises(InvalidEnvError) as info:
        make_env(PORT="notanumber").int("PORT")
    message = str(info.value)
    assert "PORT" in message
    assert "notanumber" in message


def test_bad_float_raises_invalid_error() -> None:
    with pytest.raises(InvalidEnvError):
        make_env(RATE="abc").float("RATE")


def test_unrecognised_bool_raises_invalid_error() -> None:
    with pytest.raises(InvalidEnvError) as info:
        make_env(FLAG="maybe").bool("FLAG")
    assert "FLAG" in str(info.value)


def test_bad_json_raises_naming_the_variable() -> None:
    with pytest.raises(InvalidEnvError) as info:
        make_env(CONF="{not json}").json("CONF")
    assert "CONF" in str(info.value)


def test_invalid_error_is_a_value_error() -> None:
    with pytest.raises(ValueError):
        make_env(PORT="x").int("PORT")


def test_the_module_level_env_reads_the_real_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from typedenv import env

    monkeypatch.setenv("TYPEDENV_SAMPLE", "42")
    assert env.int("TYPEDENV_SAMPLE") == 42
