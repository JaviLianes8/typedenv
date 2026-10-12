"""The public contract: one check per exported name, covering its whole promise.

``CONTRACTS`` must name exactly ``typedenv.__all__``, so a new export cannot ship
without a contract, and a removed one fails loudly.
"""

from __future__ import annotations

import importlib.resources
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

import typedenv as t


def _env() -> None:
    e = t.Env({"I": "1", "B": "off", "L": "a,b", "J": "[1]", "F": "2.5", "S": " s "})
    assert (e.int("I"), e.bool("B"), e.list("L"), e.json("J"), e.float("F")) == (
        1,
        False,
        ["a", "b"],
        [1],
        2.5,
    )
    assert e.str("S") == " s "
    assert e.str("X", "d") == "d" and e.str("X", None) is None
    assert e.str("X", required=False) is None
    calls: list[Callable[[], object]] = [lambda: e.str("X"), lambda: e.str("X", required=True)]
    for call in calls:
        with pytest.raises(t.MissingEnvError):
            call()
    assert t.Env(prefix="P_").prefixed("Q_").prefix == "P_Q_"
    assert t.Env().source is os.environ


def _env_instance() -> None:
    assert isinstance(t.env, t.Env)
    assert t.env.source is os.environ and t.env.prefix == ""


def _env_error() -> None:
    for cls in (t.MissingEnvError, t.InvalidEnvError, t.EnvValidationError, t.DotenvError):
        assert issubclass(cls, t.EnvError)
    assert issubclass(t.EnvError, Exception)


def _missing() -> None:
    error = t.MissingEnvError("PORT")
    assert isinstance(error, KeyError) and error.name == "PORT"
    assert str(error) == "required environment variable 'PORT' is not set"


def _invalid() -> None:
    error = t.InvalidEnvError("PORT", "x", "integer", "why")
    assert isinstance(error, ValueError)
    assert (error.name, error.value, error.type_name, error.reason) == (
        "PORT",
        "x",
        "integer",
        "why",
    )
    assert str(error) == "environment variable 'PORT' is not a valid integer: 'x': why"
    hidden = t.InvalidEnvError("PORT", "x", "integer", secret=True)
    assert hidden.value == "***" and "'x'" not in str(hidden)
    assert error.masked().value == "***" and error.masked().secret


def _validation() -> None:
    errors: list[t.MissingEnvError | t.InvalidEnvError] = [
        t.MissingEnvError("A"),
        t.InvalidEnvError("B", "x", "integer"),
    ]
    error = t.EnvValidationError(errors)
    assert isinstance(error, ValueError) and error.errors == tuple(errors)
    lines = str(error).splitlines()
    assert lines[0] == "2 environment variables failed validation:"
    assert lines[1:] == [f"  - {errors[0]}", f"  - {errors[1]}"]


def _dotenv_error() -> None:
    error = t.DotenvError("bad", 3, ".env")
    assert isinstance(error, ValueError)
    assert (error.reason, error.line, error.path, str(error)) == ("bad", 3, ".env", ".env:3: bad")
    assert str(t.DotenvError("bad", 3)) == "line 3: bad"


def _secret() -> None:
    s = t.Secret("v")
    assert (s.reveal(), str(s), repr(s), f"{s}") == ("v", "***", "Secret('***')", "***")
    assert s == t.Secret("v") and hash(s) == hash(t.Secret("v"))


def _load() -> None:
    @dataclass(frozen=True)
    class C:
        a: int
        b: str = "d"

    assert t.load(C, t.Env({"A": "1"})) == C(1)
    with pytest.raises(t.EnvValidationError) as info:
        t.load(C, t.Env({}))
    assert [e.name for e in info.value.errors] == ["A"]
    with pytest.raises(TypeError):
        t.load(dict, t.Env({}))


def _var() -> None:
    @dataclass
    class C:
        a: list[int] = t.var("X", default_factory=list, separator="|")
        b: int = t.var(default=2, secret=True)

    assert t.load(C, t.Env({"X": "1|2"})) == C([1, 2], 2)


def _parse_dotenv() -> None:
    assert t.parse_dotenv("A=1\nB=${A}", environ={}) == {"A": "1", "B": "1"}
    assert t.parse_dotenv("B=${Z}", environ={"Z": "z"}) == {"B": "z"}
    with pytest.raises(t.DotenvError):
        t.parse_dotenv('A="x', environ={})


def _read_dotenv(tmp: Path) -> None:
    path = tmp / ".env"
    path.write_text("A=1\n", encoding="utf-8")
    before = dict(os.environ)
    assert t.read_dotenv(path, environ={}) == {"A": "1"}
    assert dict(os.environ) == before


def _load_dotenv(tmp: Path) -> None:
    path = tmp / "contract.env"
    path.write_text("TDE_CONTRACT=1\n", encoding="utf-8")
    try:
        assert t.load_dotenv(path) == {"TDE_CONTRACT": "1"}
        assert os.environ["TDE_CONTRACT"] == "1"
        path.write_text("TDE_CONTRACT=2\n", encoding="utf-8")
        assert t.load_dotenv(path) == {}
        assert t.load_dotenv(path, override=True) == {"TDE_CONTRACT": "2"}
    finally:
        os.environ.pop("TDE_CONTRACT", None)


CONTRACTS: dict[str, Callable[..., None]] = {
    "DotenvError": _dotenv_error,
    "Env": _env,
    "EnvError": _env_error,
    "EnvValidationError": _validation,
    "InvalidEnvError": _invalid,
    "MissingEnvError": _missing,
    "Secret": _secret,
    "env": _env_instance,
    "load": _load,
    "load_dotenv": _load_dotenv,
    "parse_dotenv": _parse_dotenv,
    "read_dotenv": _read_dotenv,
    "var": _var,
}


def test_contracts_cover_exactly_the_public_api() -> None:
    assert sorted(CONTRACTS) == sorted(t.__all__)


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_contract(name: str, tmp_path: Path) -> None:
    assert hasattr(t, name)
    check = CONTRACTS[name]
    if check.__code__.co_argcount:
        check(tmp_path)
    else:
        check()


def test_version_matches_the_project_metadata() -> None:
    tomllib = pytest.importorskip("tomllib")

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    version = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    assert t.__version__ == version
    assert all(part.isdigit() for part in version.split("."))


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("typedenv").joinpath("py.typed").is_file()


def test_the_console_script_is_declared() -> None:
    tomllib = pytest.importorskip("tomllib")

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts == {"typedenv": "typedenv._cli:main"}
    from typedenv._cli import main

    assert callable(main)
