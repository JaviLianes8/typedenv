"""Real end to end: build the wheel, install it into a throwaway venv, run the script.

No mocks and no source tree on the path. The wheel is built from the project, pip
installs it (offline, it has no dependencies) into a fresh virtual environment, and
the installed ``typedenv`` executable is driven over subprocess with crafted
environments.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
from collections.abc import Mapping
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.e2e


def _bin(env_dir: Path, name: str) -> Path:
    if sys.platform == "win32":
        return env_dir / "Scripts" / f"{name}.exe"
    return env_dir / "bin" / name


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return the venv directory with the freshly built wheel installed."""
    dist = tmp_path_factory.mktemp("dist")
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(PROJECT_ROOT)],
        check=True,
        capture_output=True,
        timeout=600,
    )
    wheels = list(dist.glob("typedenv-*.whl"))
    assert len(wheels) == 1, wheels
    env_dir = tmp_path_factory.mktemp("venv")
    venv.create(env_dir, with_pip=True)
    subprocess.run(
        [str(_bin(env_dir, "python")), "-m", "pip", "install", "--no-index", str(wheels[0])],
        check=True,
        capture_output=True,
        timeout=600,
    )
    return env_dir


def _env(extra: Mapping[str, str]) -> dict[str, str]:
    base = {k.upper(): os.environ[k] for k in ("SYSTEMROOT", "TEMP", "TMP") if k in os.environ}
    return {**base, "PYTHONIOENCODING": "utf-8", **extra}


def _run(
    installed: Path, env: Mapping[str, str], *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(_bin(installed, "typedenv")), *args],
        env=_env(env),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=cwd,
    )


def test_the_wheel_installs_the_console_script(installed: Path) -> None:
    assert _bin(installed, "typedenv").is_file()
    result = _run(installed, {}, "--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "typedenv 0.2.0"


def test_installed_check_passes_and_fails_on_real_environments(
    installed: Path, tmp_path: Path
) -> None:
    spec = tmp_path / "env.spec"
    spec.write_text("API_KEY secret\nPORT int\nDEBUG bool optional\n", encoding="utf-8")
    ok = _run(installed, {"API_KEY": "hunter2", "PORT": "80"}, "check", str(spec))
    assert ok.returncode == 0, ok.stderr
    assert "all 3 variables ok" in ok.stdout
    bad = _run(installed, {"API_KEY": "hunter2", "PORT": "x"}, "check", str(spec), "--show-values")
    assert bad.returncode == 1
    assert "1 of 3 variables failed" in bad.stderr
    assert "hunter2" not in bad.stdout + bad.stderr


def test_installed_check_json(installed: Path, tmp_path: Path) -> None:
    spec = tmp_path / "env.spec"
    spec.write_text("PORT int\n", encoding="utf-8")
    result = _run(installed, {}, "check", str(spec), "--format", "json")
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["variables"][0]["status"] == "missing"


def test_installed_check_against_a_dataclass(installed: Path, tmp_path: Path) -> None:
    (tmp_path / "deploy_settings.py").write_text(
        "from dataclasses import dataclass\n"
        "from datetime import timedelta\n"
        "@dataclass(frozen=True)\n"
        "class Settings:\n"
        "    timeout: timedelta\n"
        "    workers: int | None = None\n",
        encoding="utf-8",
    )
    target = "deploy_settings:Settings"
    ok = _run(installed, {"TIMEOUT": "30s"}, "check", target, cwd=tmp_path)
    assert ok.returncode == 0, ok.stderr
    bad = _run(installed, {"TIMEOUT": "soon", "WORKERS": "many"}, "check", target, cwd=tmp_path)
    assert bad.returncode == 1
    assert "2 of 2 variables failed" in bad.stderr


def test_installed_get_with_env_file(installed: Path, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('export TIMEOUT="1h30m"  # deploy\n', encoding="utf-8")
    result = _run(
        installed, {}, "get", "TIMEOUT", "--type", "duration", "--env-file", str(env_file)
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "5400"


def test_installed_get_error_is_on_stderr(installed: Path) -> None:
    result = _run(installed, {"PORT": "eighty"}, "get", "PORT", "--type", "int")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "not a valid integer" in result.stderr


def test_installed_library_reads_a_crafted_environment(installed: Path) -> None:
    code = (
        "import typedenv; from typedenv import env\n"
        "print(typedenv.__version__, env.int('PORT'), env.secret('TOKEN'))"
    )
    result = subprocess.run(
        [str(_bin(installed, "python")), "-c", code],
        env=_env({"PORT": "8080", "TOKEN": "hunter2"}),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["0.2.0", "8080", "***"]
