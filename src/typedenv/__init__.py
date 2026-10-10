"""Tiny typed reader for environment variables with mypy-inferred return types."""

from __future__ import annotations

from ._env import Env, env
from ._errors import EnvError, InvalidEnvError, MissingEnvError

__version__ = "0.1.0"

__all__ = [
    "Env",
    "EnvError",
    "InvalidEnvError",
    "MissingEnvError",
    "env",
]
