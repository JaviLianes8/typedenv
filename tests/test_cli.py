"""The typedenv command, run in real child processes with crafted environments."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from procs import run_cli, run_python

SPEC = """\
# deployment contract
DATABASE_URL  secret
PORT          int       optional
DEBUG         bool
LEVEL         choice:debug,info
HOSTS         list:;
TIMEOUT       duration  optional
"""
GOOD = {
    "DATABASE_URL": "postgres://hunter2@db",
    "PORT": "8080",
    "DEBUG": "on",
    "LEVEL": "info",
    "HOSTS": "a;b",
}


@pytest.fixture
def spec(tmp_path: Path) -> Path:
    path = tmp_path / "env.spec"
    path.write_text(SPEC, encoding="utf-8")
    return path


def test_check_passes_when_everything_is_valid(spec: Path) -> None:
    result = run_cli(GOOD, "check", str(spec))
    assert result.returncode == 0, result.stderr
    assert "all 6 variables ok" in result.stdout
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert lines[0].split()[:3] == ["ok", "DATABASE_URL", "secret"]
    assert lines[5].split()[:2] == ["unset", "TIMEOUT"]


def test_check_reports_every_failure_and_exits_1(spec: Path) -> None:
    env = {**GOOD, "PORT": "eighty", "LEVEL": "loud"}
    del env["DEBUG"]
    result = run_cli(env, "check", str(spec))
    assert result.returncode == 1
    assert "3 of 6 variables failed" in result.stderr
    rows = {line.split()[1]: line.split()[0] for line in result.stdout.splitlines()}
    assert rows == {
        "DATABASE_URL": "ok",
        "PORT": "invalid",
        "DEBUG": "missing",
        "LEVEL": "invalid",
        "HOSTS": "ok",
        "TIMEOUT": "unset",
    }


def test_check_never_prints_a_secret(spec: Path) -> None:
    result = run_cli(GOOD, "check", str(spec), "--show-values")
    assert "hunter2" not in result.stdout + result.stderr
    assert "8080" in result.stdout
    as_json = run_cli(GOOD, "check", str(spec), "--show-values", "--format", "json")
    assert "hunter2" not in as_json.stdout


def test_check_hides_values_unless_asked(spec: Path) -> None:
    result = run_cli(GOOD, "check", str(spec))
    assert "8080" not in result.stdout


def test_check_json_report(spec: Path) -> None:
    result = run_cli({**GOOD, "PORT": "x"}, "check", str(spec), "--format", "json")
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["ok"] is False
    port = next(row for row in report["variables"] if row["name"] == "PORT")
    assert port["status"] == "invalid"
    assert "not a valid integer" in port["error"]
    assert "value" not in port


def test_check_quiet_prints_nothing(spec: Path) -> None:
    result = run_cli({}, "check", str(spec), "--quiet")
    assert result.returncode == 1
    assert result.stdout == result.stderr == ""


def test_check_prefix_and_env_file(spec: Path, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("APP_DEBUG=no\nAPP_LEVEL=debug\nAPP_HOSTS=h\n", encoding="utf-8")
    env = {"APP_DATABASE_URL": "x", "APP_LEVEL": "info"}
    result = run_cli(env, "check", str(spec), "--prefix", "APP_", "--env-file", str(env_file))
    assert result.returncode == 0, result.stdout + result.stderr
    shown = run_cli(env, "get", "LEVEL", "--prefix", "APP_", "--env-file", str(env_file))
    assert shown.stdout.strip() == "info"


def test_check_empty_is_unset(spec: Path) -> None:
    env = {**GOOD, "PORT": ""}
    assert run_cli(env, "check", str(spec)).returncode == 1
    assert run_cli(env, "check", str(spec), "--empty-is-unset").returncode == 0


def test_check_a_dataclass_by_import_path(tmp_path: Path) -> None:
    (tmp_path / "appsettings.py").write_text(
        "from dataclasses import dataclass\n"
        "from typedenv import Secret\n"
        "@dataclass\n"
        "class Settings:\n"
        "    token: Secret\n"
        "    port: int = 80\n",
        encoding="utf-8",
    )
    ok = run_cli({"TOKEN": "t", "PORT": "1"}, "check", "appsettings:Settings", cwd=tmp_path)
    assert ok.returncode == 0, ok.stderr
    bad = run_cli({"PORT": "x"}, "check", "appsettings:Settings", cwd=tmp_path)
    assert bad.returncode == 1
    assert "missing" in bad.stdout and "invalid" in bad.stdout


@pytest.mark.parametrize(
    ("env", "args", "expected"),
    [
        ({"DEBUG": "Yes"}, ["DEBUG", "--type", "bool"], "true"),
        ({}, ["PORT", "--type", "int", "--default", "8080"], "8080"),
        ({"T": "1h30m"}, ["T", "--type", "duration"], "5400"),
        ({"T": "250ms"}, ["T", "--type", "duration"], "0.25"),
        ({"H": "a, b"}, ["H", "--type", "list"], "a\nb"),
        ({"C": '{"a": [1]}'}, ["C", "--type", "json"], '{"a": [1]}'),
        ({"P": " 1.50 "}, ["P", "--type", "decimal"], "1.50"),
        ({"M": "prod"}, ["M", "--type", "choice:dev,prod"], "prod"),
        ({"S": "raw value"}, ["S"], "raw value"),
    ],
)
def test_get_prints_the_canonical_value(
    env: dict[str, str], args: list[str], expected: str
) -> None:
    result = run_cli(env, "get", *args)
    assert result.returncode == 0, result.stderr
    assert result.stdout.rstrip("\n") == expected


def test_get_errors_go_to_stderr() -> None:
    missing = run_cli({}, "get", "PORT", "--type", "int")
    assert missing.returncode == 1
    assert missing.stdout == ""
    assert "PORT" in missing.stderr
    bad = run_cli({"PORT": "hunter2"}, "get", "PORT", "--type", "int", "--secret")
    assert bad.returncode == 1
    assert "hunter2" not in bad.stderr
    bad_default = run_cli({}, "get", "PORT", "--type", "int", "--default", "x")
    assert bad_default.returncode == 1


@pytest.mark.parametrize(
    "args",
    [
        ["get", "X", "--type", "nope"],
        ["get", "X", "--type", "choice:"],
        ["check", "does/not/exist.spec"],
        ["check", "no_such_module_xyz:Settings"],
        ["frobnicate"],
        [],
    ],
)
def test_usage_errors_exit_1_on_stderr(args: list[str]) -> None:
    result = run_cli({}, *args)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr


def test_bad_spec_line_is_named(tmp_path: Path) -> None:
    path = tmp_path / "bad.spec"
    path.write_text("A int\nB int mandatory\n", encoding="utf-8")
    result = run_cli({}, "check", str(path))
    assert result.returncode == 1
    assert f"{path}:2:" in result.stderr


def test_help_has_runnable_examples() -> None:
    result = run_cli({}, "--help")
    assert result.returncode == 0
    assert "typedenv check env.spec" in result.stdout
    assert "typedenv get PORT --type int --default 8080" in result.stdout


def test_python_dash_m_runs_the_same_command() -> None:
    result = run_python(
        "import runpy; runpy.run_module('typedenv', run_name='__main__')", {}, "--version"
    )
    assert result.returncode == 0
    assert result.stdout.strip().startswith("typedenv ")
