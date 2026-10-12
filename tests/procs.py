"""Helpers for tests that run real child processes with a crafted environment."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def child_env(extra: Mapping[str, str]) -> dict[str, str]:
    """A minimal environment for a child Python process plus ``extra``.

    Only what the interpreter needs to start is inherited (SYSTEMROOT on Windows),
    so the variables under test are exactly the ones the test wrote.
    """
    base: dict[str, str] = {"PYTHONPATH": str(SRC), "PYTHONIOENCODING": "utf-8"}
    for name in ("SYSTEMROOT", "SystemRoot", "TEMP", "TMP"):
        if name in os.environ:
            base[name.upper()] = os.environ[name]
    base.update(extra)
    return base


def run_python(
    code: str, env: Mapping[str, str], *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``code`` in a fresh interpreter whose whole environment is ``child_env(env)``."""
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        env=child_env(env),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=cwd,
    )


def run_cli(
    env: Mapping[str, str], *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``python -m typedenv._cli`` from the source tree in a crafted environment."""
    return run_python(
        "from typedenv._cli import main; raise SystemExit(main())", env, *args, cwd=cwd
    )
