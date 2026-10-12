"""Typed, zero-dependency reader for environment variables with mypy-inferred types."""

from __future__ import annotations

from ._env import Env, env
from ._errors import (
    EnvError,
    InvalidEnvError,
    MissingEnvError,
)
from ._secret import Secret

__version__ = "0.1.0"

__all__ = [
    "Env",
    "EnvError",
    "InvalidEnvError",
    "MissingEnvError",
    "Secret",
    "env",
]
