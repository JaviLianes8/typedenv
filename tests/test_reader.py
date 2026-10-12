"""Prefix scoping, empty-value handling, presence checks and the reader's repr."""

from __future__ import annotations

import os

import pytest

from typedenv import Env, InvalidEnvError, MissingEnvError


def test_prefix_is_prepended_to_every_name() -> None:
    reader = Env({"APP_PORT": "80", "PORT": "1"}, prefix="APP_")
    assert reader.int("PORT") == 80
    assert reader.full_name("PORT") == "APP_PORT"


def test_errors_name_the_prefixed_variable() -> None:
    reader = Env({"APP_PORT": "eighty"}, prefix="APP_")
    with pytest.raises(InvalidEnvError) as info:
        reader.int("PORT")
    assert info.value.name == "APP_PORT"
    with pytest.raises(MissingEnvError) as missing:
        reader.int("WORKERS")
    assert missing.value.name == "APP_WORKERS"


def test_prefixed_nests_and_keeps_the_source() -> None:
    source = {"APP_DB_HOST": "db"}
    reader = Env(source, empty_is_unset=True).prefixed("APP_").prefixed("DB_")
    assert reader.prefix == "APP_DB_"
    assert reader.str("HOST") == "db"
    assert reader.source is source
    assert reader.empty_is_unset is True
    assert isinstance(reader, Env)


def test_empty_value_is_returned_by_default() -> None:
    reader = Env({"NAME": ""})
    assert reader.str("NAME") == ""
    assert reader.str("NAME", "fallback") == ""
    assert reader.is_set("NAME")
    with pytest.raises(InvalidEnvError):
        reader.int("NAME")


def test_empty_is_unset_treats_empty_as_missing() -> None:
    reader = Env({"NAME": "", "PORT": ""}, empty_is_unset=True)
    assert reader.str("NAME", "fallback") == "fallback"
    assert reader.int("PORT", 80) == 80
    assert not reader.is_set("NAME")
    assert reader.raw("NAME") is None
    with pytest.raises(MissingEnvError):
        reader.int("PORT")


def test_raw_and_contains() -> None:
    reader = Env({"A": "1"})
    assert reader.raw("A") == "1"
    assert reader.raw("B") is None
    assert "A" in reader
    assert "B" not in reader
    assert 3 not in reader


def test_default_source_is_the_live_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = Env()
    assert reader.source is os.environ
    monkeypatch.setenv("TYPEDENV_LIVE", "7")
    assert reader.int("TYPEDENV_LIVE") == 7


def test_repr_never_shows_values() -> None:
    reader = Env({"TOKEN": "hunter2"}, prefix="APP_")
    text = repr(reader)
    assert "hunter2" not in text
    assert "APP_" in text
    assert "os.environ" in repr(Env())


def test_missing_error_str_is_not_double_quoted() -> None:
    with pytest.raises(MissingEnvError) as info:
        Env({}).str("TOKEN")
    assert str(info.value) == "required environment variable 'TOKEN' is not set"


@pytest.mark.parametrize("word", ["enable", "Enabled", "DISABLE", "disabled"])
def test_bool_vocabulary_matches_boolish(word: str) -> None:
    assert Env({"F": word}).bool("F") is word.lower().startswith("enable")


def test_bool_rejects_empty_and_unknown() -> None:
    for raw in ("", "maybe", "2"):
        with pytest.raises(InvalidEnvError):
            Env({"F": raw}).bool("F")


def test_json_error_reports_position_not_value() -> None:
    with pytest.raises(InvalidEnvError) as info:
        Env({"C": '{"a": }'}).json("C", secret=True)
    assert "line 1 column" in str(info.value)
