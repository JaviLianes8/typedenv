"""load() and var(): populate a plain dataclass and report every failure at once."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Optional

import pytest

from typedenv import (
    Env,
    EnvValidationError,
    InvalidEnvError,
    MissingEnvError,
    Secret,
    load,
    var,
)


class Level(enum.Enum):
    DEBUG = "debug"
    INFO = "info"


@dataclass(frozen=True)
class Settings:
    database_url: Secret
    port: int = 8080
    debug: bool = False
    workers: int | None = None
    hosts: list[str] = field(default_factory=list)
    timeout: timedelta = timedelta(seconds=5)
    level: Level = Level.INFO
    mode: Literal["dev", "prod"] = "dev"
    api_key: str = var("SERVICE_TOKEN", default="", secret=True)
    ports: tuple[int, ...] = var(default=(), separator=";")


def test_reads_every_field_from_its_upper_cased_name() -> None:
    source = {
        "DATABASE_URL": "postgres://u:p@h/db",
        "PORT": "9000",
        "DEBUG": "yes",
        "WORKERS": "4",
        "HOSTS": "a, b",
        "TIMEOUT": "1m",
        "LEVEL": "DEBUG",
        "MODE": "prod",
        "SERVICE_TOKEN": "tok",
        "PORTS": "1;2",
    }
    settings = load(Settings, Env(source))
    assert settings.database_url.reveal() == "postgres://u:p@h/db"
    assert settings.port == 9000
    assert settings.debug is True
    assert settings.workers == 4
    assert settings.hosts == ["a", "b"]
    assert settings.timeout == timedelta(minutes=1)
    assert settings.level is Level.DEBUG
    assert settings.mode == "prod"
    assert settings.api_key == "tok"
    assert settings.ports == (1, 2)


def test_defaults_fill_unset_fields() -> None:
    settings = load(Settings, Env({"DATABASE_URL": "x"}))
    assert settings == Settings(database_url=Secret("x"))
    assert settings.hosts == []
    assert settings.workers is None


def test_every_failure_is_reported_in_one_exception() -> None:
    source = {"PORT": "eighty", "DEBUG": "maybe", "MODE": "staging"}
    with pytest.raises(EnvValidationError) as info:
        load(Settings, Env(source))
    errors = info.value.errors
    assert [type(error) for error in errors] == [
        MissingEnvError,
        InvalidEnvError,
        InvalidEnvError,
        InvalidEnvError,
    ]
    assert [error.name for error in errors] == ["DATABASE_URL", "PORT", "DEBUG", "MODE"]
    message = str(info.value)
    assert message.startswith("4 environment variables failed validation:")
    for name in ("DATABASE_URL", "PORT", "DEBUG", "MODE"):
        assert name in message
    assert isinstance(info.value, ValueError)


def test_secret_fields_never_reach_the_error_or_the_repr() -> None:
    source = {"DATABASE_URL": "hunter2-db", "SERVICE_TOKEN": "hunter2-tok", "PORT": "bad"}
    settings_repr = repr(load(Settings, Env({"DATABASE_URL": "hunter2-db"})))
    assert "hunter2" not in settings_repr

    @dataclass
    class Strict:
        token: int = var("SERVICE_TOKEN", secret=True)

    with pytest.raises(EnvValidationError) as info:
        load(Strict, Env(source))
    assert "hunter2" not in str(info.value)
    assert info.value.__context__ is None


def test_prefix_comes_from_the_reader() -> None:
    settings = load(Settings, Env({"APP_DATABASE_URL": "x", "APP_PORT": "1"}, prefix="APP_"))
    assert settings.port == 1
    with pytest.raises(EnvValidationError) as info:
        load(Settings, Env({}, prefix="APP_"))
    assert info.value.errors[0].name == "APP_DATABASE_URL"


def test_optional_annotation_without_default_is_optional() -> None:
    @dataclass
    class Opt:
        a: Optional[int]  # noqa: UP045
        b: Decimal | None
        c: Path | None = None

    assert load(Opt, Env({"B": "1.5"})) == Opt(a=None, b=Decimal("1.5"), c=None)


def test_dict_fields_need_a_json_object() -> None:
    @dataclass
    class Conf:
        limits: dict[str, Any]

    assert load(Conf, Env({"LIMITS": '{"a": 1}'})).limits == {"a": 1}
    with pytest.raises(EnvValidationError):
        load(Conf, Env({"LIMITS": "[1]"}))


def test_list_items_are_parsed_and_errors_name_the_variable() -> None:
    @dataclass
    class Nums:
        values: list[float] = var(default_factory=list)

    assert load(Nums, Env({"VALUES": "1, 2.5"})).values == [1.0, 2.5]
    with pytest.raises(EnvValidationError) as info:
        load(Nums, Env({"VALUES": "1,x"}))
    assert info.value.errors[0].name == "VALUES"


def test_uses_the_process_environment_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclass
    class One:
        typedenv_probe: int

    monkeypatch.setenv("TYPEDENV_PROBE", "5")
    assert load(One).typedenv_probe == 5


def test_init_false_fields_are_skipped() -> None:
    @dataclass
    class Derived:
        port: int = 1
        url: str = field(init=False, default="")

    assert load(Derived, Env({"URL": "ignored"})).url == ""


@pytest.mark.parametrize("annotation", [set[str], list[list[str]], tuple[int, str], bytes, object])
def test_unsupported_annotations_raise_type_error(annotation: Any) -> None:
    namespace: dict[str, Any] = {"__annotations__": {"value": annotation}}
    cls: type[Any] = dataclass(type("Bad", (), namespace))
    with pytest.raises(TypeError):
        load(cls, Env({"VALUE": "x"}))


def test_non_dataclasses_are_rejected() -> None:
    with pytest.raises(TypeError):
        load(int, Env({}))
    with pytest.raises(TypeError):
        load(Settings(database_url=Secret("x")), Env({}))  # type: ignore[arg-type]


def test_var_rejects_two_defaults() -> None:
    with pytest.raises(ValueError):
        var(default=1, default_factory=list)


def test_var_without_default_is_required() -> None:
    @dataclass
    class Req:
        port: int = var("HTTP_PORT")

    with pytest.raises(EnvValidationError) as info:
        load(Req, Env({}))
    assert info.value.errors[0].name == "HTTP_PORT"
    assert load(Req, Env({"HTTP_PORT": "1"})).port == 1
