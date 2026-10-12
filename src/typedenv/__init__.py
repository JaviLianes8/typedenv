"""Typed, zero-dependency reader for environment variables with mypy-inferred types."""

from __future__ import annotations

from ._dotenv import load_dotenv, parse_dotenv, read_dotenv
from ._env import Env, env
from ._errors import (
    DotenvError,
    EnvError,
    EnvValidationError,
    InvalidEnvError,
    MissingEnvError,
)
from ._secret import Secret
from ._settings import load, var

__version__ = "0.1.0"

__all__ = [
    "DotenvError",
    "Env",
    "EnvError",
    "EnvValidationError",
    "InvalidEnvError",
    "MissingEnvError",
    "Secret",
    "env",
    "load",
    "load_dotenv",
    "parse_dotenv",
    "read_dotenv",
    "var",
]
