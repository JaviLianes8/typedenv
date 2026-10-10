# typedenv

Tiny typed reader for environment variables with mypy-inferred return types, zero dependencies.

## Install

```
pip install typedenv
```

## Usage

```python
from typedenv import env

# Required: raises MissingEnvError if DATABASE_URL is unset. Type is str.
database_url = env.str("DATABASE_URL")

# With a default. Type follows the default, so this is int.
port = env.int("PORT", 8080)

# Optional: pass None (or required=False) and the type widens to int | None.
workers = env.int("WORKERS", None)

# Booleans accept true/false, yes/no, on/off, 1/0 (any case).
debug = env.bool("DEBUG", False)

# Lists split on a separator (comma by default).
hosts = env.list("ALLOWED_HOSTS", separator=",")

# JSON via the standard library.
limits = env.json("RATE_LIMITS", {})
```

The return type is inferred from the call, so a type checker knows the difference:

```python
reveal_type(env.int("PORT"))        # int
reveal_type(env.int("PORT", None))  # int | None
```

Point it at any mapping instead of `os.environ`, which makes tests trivial:

```python
from typedenv import Env

cfg = Env(source={"PORT": "9090"})
assert cfg.int("PORT") == 9090
```

Errors name the offending variable:

```
MissingEnvError: required environment variable 'DATABASE_URL' is not set
InvalidEnvError: environment variable 'PORT' is not a valid integer: 'eighty'
```

`MissingEnvError` is also a `KeyError` and `InvalidEnvError` is also a `ValueError`, so
existing handlers keep working.

## Why

Reading config from the environment is a one-liner until you want three things at once:
the value typed, a missing required variable to fail loudly, and your type checker to
agree with both. The existing options each give up one of those or pull in dependencies:

- `environs` needs `marshmallow` and `python-dotenv`.
- `environ-config` is built on `attrs`.
- `pydantic-settings` pulls in `pydantic-core`.
- `typenv`, the closest in spirit, depends on `python-dotenv` and has not shipped since
  2021.

`typedenv` is one small module, has no runtime dependencies, ships `py.typed`, and uses
`@overload` so `env.int("X")` is `int`, `env.int("X", None)` is `int | None`, and
`env.int("X", required=True)` is `int`, with no casts at the call site. Reach for it when
you want typed environment access without adding a settings framework to the project.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
