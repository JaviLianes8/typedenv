"""Ground truth: real child processes with a crafted environment, read via typedenv.

Nothing is mocked. Each test starts a fresh interpreter whose entire environment is
written by the test, and the child reads it back through the library.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from procs import run_python

READ = "import sys; from typedenv import env; print(repr(env.raw(sys.argv[1])))"


def test_values_cross_the_process_boundary_as_strings() -> None:
    code = "from typedenv import env; print(env.int('PORT') + 1, env.bool('DEBUG'))"
    result = run_python(code, {"PORT": "8080", "DEBUG": "enabled"})
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["8081", "True"]


def test_empty_is_set_and_distinct_from_unset() -> None:
    code = (
        "from typedenv import Env\n"
        "e = Env(); u = Env(empty_is_unset=True)\n"
        "print(repr(e.str('EMPTY')), e.is_set('EMPTY'), e.is_set('ABSENT'),"
        " u.is_set('EMPTY'), u.str('EMPTY', 'fallback'))"
    )
    result = run_python(code, {"EMPTY": ""})
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["''", "True", "False", "False", "fallback"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows names are case-insensitive")
def test_windows_names_are_case_insensitive() -> None:
    result = run_python(READ, {"MixedCase": "1"}, "MIXEDCASE")
    assert result.stdout.strip() == "'1'"
    lower = run_python(READ, {"MixedCase": "1"}, "mixedcase")
    assert lower.stdout.strip() == "'1'"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX names are case-sensitive")
def test_posix_names_are_case_sensitive() -> None:
    result = run_python(READ, {"MixedCase": "1"}, "MIXEDCASE")
    assert result.stdout.strip() == "None"
    both = run_python(READ, {"name": "lower", "NAME": "upper"}, "name")
    assert both.stdout.strip() == "'lower'"


def test_a_plain_dict_source_is_always_exact() -> None:
    code = "from typedenv import Env; print(Env({'MixedCase': '1'}).raw('MIXEDCASE'))"
    assert run_python(code, {}).stdout.strip() == "None"


def test_values_longer_than_the_windows_putenv_limit_still_arrive() -> None:
    # CreateProcess and execve both carry values past 32,767 characters; only
    # os.putenv on Windows refuses them, which load_dotenv reports up front.
    code = "from typedenv import env; print(len(env.str('BIG')))"
    result = run_python(code, {"BIG": "x" * 40000})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "40000"


def test_unicode_values_round_trip() -> None:
    code = "from typedenv import env; print(env.str('WORD').encode('unicode_escape').decode())"
    result = run_python(code, {"WORD": "caf\u00e9 \u65e5\u672c"})
    assert result.stdout.strip() == "caf\\xe9 \\u65e5\\u672c"


def test_load_reports_every_failure_from_a_real_environment(tmp_path: Path) -> None:
    (tmp_path / "cfg.py").write_text(
        "from dataclasses import dataclass\n"
        "from typedenv import Secret\n"
        "@dataclass(frozen=True)\n"
        "class Cfg:\n"
        "    token: Secret\n"
        "    port: int\n"
        "    debug: bool = False\n",
        encoding="utf-8",
    )
    code = (
        "import sys; sys.path.insert(0, sys.argv[1])\n"
        "from cfg import Cfg; from typedenv import load, EnvValidationError\n"
        "try:\n    load(Cfg)\nexcept EnvValidationError as e:\n"
        "    print(len(e.errors)); print(e)\n"
    )
    result = run_python(code, {"PORT": "x", "DEBUG": "maybe"}, str(tmp_path))
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "3"
    assert "TOKEN" in result.stdout and "PORT" in result.stdout and "DEBUG" in result.stdout


@pytest.mark.parametrize(
    "call",
    [
        "env.int('TOKEN', secret=True)",
        "env.json('TOKEN', secret=True)",
        "env.decimal('TOKEN', secret=True)",
        "env.bool('TOKEN', secret=True)",
    ],
)
def test_uncaught_secret_errors_leave_no_trace_in_the_traceback(call: str) -> None:
    secret = "hunter2-{very-secret"
    result = run_python(f"from typedenv import env; {call}", {"TOKEN": secret})
    assert result.returncode == 1
    assert "InvalidEnvError" in result.stderr
    assert "hunter2" not in result.stderr
    assert "hunter2" not in result.stdout


def test_uncaught_load_error_keeps_secret_fields_hidden(tmp_path: Path) -> None:
    (tmp_path / "cfg.py").write_text(
        "from dataclasses import dataclass\n"
        "from typedenv import var\n"
        "@dataclass\n"
        "class Cfg:\n"
        "    pin: int = var('PIN', secret=True)\n",
        encoding="utf-8",
    )
    code = "import sys; sys.path.insert(0, sys.argv[1]); from cfg import Cfg; " + (
        "from typedenv import load; load(Cfg)"
    )
    result = run_python(code, {"PIN": "hunter2"}, str(tmp_path))
    assert result.returncode == 1
    assert "EnvValidationError" in result.stderr
    assert "hunter2" not in result.stderr


def test_load_dotenv_writes_into_the_real_process_environment(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A=from-file\nB=${A}-x\nKEEP=file\n", encoding="utf-8")
    code = (
        "import os, sys, subprocess\n"
        "from typedenv import load_dotenv\n"
        "load_dotenv(sys.argv[1])\n"
        "out = subprocess.run([sys.executable, '-c',"
        ' \'import os; print(os.environ["A"], os.environ["B"], os.environ["KEEP"])\'],'
        " capture_output=True, text=True).stdout\n"
        "print(out.strip())\n"
    )
    result = run_python(code, {"KEEP": "env"}, str(env_file))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "from-file from-file-x env"
