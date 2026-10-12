# typedenv

Typed reader for environment variables with mypy-inferred return types, settings
dataclasses, `.env` files and a checker CLI. Zero dependencies.

## Install

```
pip install typedenv
```

## Read one variable

```python
from typedenv import env

database_url = env.str("DATABASE_URL")  # str, raises MissingEnvError if unset
port = env.int("PORT", 8080)  # int, the default when unset
workers = env.int("WORKERS", None)  # int | None
debug = env.bool("DEBUG", False)  # true/false, yes/no, on/off, 1/0, ...
hosts = env.list("ALLOWED_HOSTS")  # split on "," and trimmed
timeout = env.duration("TIMEOUT", None)  # "90", "250ms", "1h30m" -> timedelta
api_key = env.secret("API_KEY")  # Secret: prints as ***
```

Every getter takes the same arguments and the static type follows the call:

| call | type | when unset |
| --- | --- | --- |
| `env.int("X")` | `int` | raises `MissingEnvError` |
| `env.int("X", required=True)` | `int` | raises `MissingEnvError` |
| `env.int("X", 8080)` | `int` | `8080` |
| `env.int("X", None)` | `int \| None` | `None` |
| `env.int("X", required=False)` | `int \| None` | `None` |

| getter | returns | accepts |
| --- | --- | --- |
| `str` | `str` | anything, returned as is (`""` stays `""`) |
| `int` | `int` | base-10 integer, surrounding whitespace ignored |
| `float` | `float` | anything `float()` accepts |
| `bool` | `bool` | `true/false`, `yes/no`, `on/off`, `1/0`, `y/n`, `t/f`, `enable(d)/disable(d)`, any case |
| `decimal` | `Decimal` | exact decimal; `NaN` and infinities are rejected |
| `path` | `Path` | non-empty path, taken literally (no `~` expansion) |
| `duration` | `timedelta` | seconds (`90`, `1.5`) or units `w d h m s ms` from largest to smallest (`1h30m`) |
| `enum` | your `Enum` | member name in any case, or the member value as text |
| `list` | `list[str]` | split on `separator=` (default `,`), items trimmed, `""` is `[]` |
| `json` | `Any` | JSON, parsed by the standard library |
| `secret` | `Secret` | anything, wrapped so it never prints |

The boolean words match the default vocabulary of
[boolish](https://pypi.org/project/boolish/), without depending on it.

## Load a settings dataclass

```python
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from typedenv import Env, Secret, load, var


@dataclass(frozen=True)
class Settings:
    database_url: Secret  # DATABASE_URL, required
    port: int = 8080  # PORT
    workers: int | None = None  # WORKERS, optional
    hosts: list[str] = field(default_factory=list)
    timeout: timedelta = timedelta(seconds=5)
    mode: Literal["dev", "prod"] = "dev"
    token: str = var("SERVICE_TOKEN", default="", secret=True)
    ports: tuple[int, ...] = var(default=(), separator=";")


settings = load(Settings)  # from os.environ
settings = load(Settings, Env(prefix="APP_"))  # APP_DATABASE_URL, APP_PORT, ...
```

There is no base class and no metaclass: `load` reads `dataclasses.fields()` and the
annotations. The variable name is the field name upper-cased, or `var(name=...)`. A
field with a default, a `default_factory` or an `X | None` annotation is optional.
Supported annotations: `str`, `int`, `float`, `bool`, `Decimal`, `Path`, `timedelta`,
`Secret`, any `Enum`, `Literal["a", "b"]`, `dict[...]` (a JSON object), and `list[X]` or
`tuple[X, ...]` of a scalar type. Anything else raises `TypeError` when `load` runs.

`load` reads every field before raising, so one run reports every problem:

```
EnvValidationError: 3 environment variables failed validation:
  - required environment variable 'DATABASE_URL' is not set
  - environment variable 'PORT' is not a valid integer: 'eighty'
  - environment variable 'MODE' is not a valid choice: 'staging': expected one of dev, prod
```

The individual errors are in `error.errors`. If you lint with ruff, add
`extend-immutable-calls = ["typedenv.var"]` under `[tool.ruff.lint.flake8-bugbear]`
so `var()` is treated like `field()`.

## Secrets

`secret=True` on any getter, `var(secret=True)`, or a `Secret` annotation keeps the
value out of error messages, the error's `value` attribute (`"***"`) and the exception
chain, so even an uncaught traceback does not show it. A `Secret` prints as `***` in
`str`, `repr`, f-strings and dataclass reprs; call `.reveal()` where the real value is
needed. It compares in constant time and refuses to be pickled. `secret=True` alone only
protects errors; annotate the field as `Secret` to keep it out of the dataclass repr too.

## Prefixes, empty values and presence

```python
app = Env(prefix="APP_")  # app.int("PORT") reads APP_PORT
db = app.prefixed("DB_")  # db.str("HOST") reads APP_DB_HOST
strict = Env(empty_is_unset=True)  # KEY= counts as unset
env.raw("PORT")  # the unparsed string, or None
env.is_set("PORT"), "PORT" in env  # presence
cfg = Env({"PORT": "9090"})  # any mapping instead of os.environ
```

## Platform facts

- **Names**: `os.environ` is case-insensitive on Windows (keys are stored upper-case)
  and case-sensitive on POSIX, so `env.str("path")` finds `PATH` on Windows only. A
  plain `dict` source is always exact.
- **Values** are always strings; there is no `None` in the environment. A variable can
  be set to `""`, which is different from unset unless you pass `empty_is_unset=True`.
- **Length**: on Windows `os.environ` refuses an entry whose `NAME=value` is longer
  than 32,767 characters, although a child process can receive longer values through
  `subprocess` `env=`. `load_dotenv` checks this up front and raises `DotenvError`.

## `.env` files

```python
from typedenv import load_dotenv, parse_dotenv, read_dotenv

load_dotenv(".env")  # set what is not already set; returns what it set
load_dotenv(".env", override=True)  # the file wins
values = read_dotenv(".env")  # dict, environment untouched
```

The supported syntax is a subset of python-dotenv 1.x, tested line by line against
python-dotenv itself:

| syntax | result |
| --- | --- |
| blank lines, `# comment` lines | ignored |
| `export KEY=value`, `KEY = value` | `export` and spaces around `=` are allowed |
| `KEY=plain value  # note` | `plain value` (an inline `#` needs a space before it) |
| `KEY='literal \n $X'` | taken literally; only `\'` and `\\` are escapes |
| `KEY="a\tb ${X}"` | escapes `\\ \' \" \a \b \f \n \r \t \v`, then expansion |
| `${NAME}`, `${NAME:-default}` | earlier keys, then the environment; unknown is `""` |
| `KEY` (no `=`) | skipped |
| `KEY=` | `""` |

Expansion order follows python-dotenv: `read_dotenv` and `parse_dotenv` prefer earlier
keys in the file, `load_dotenv` prefers the existing environment unless `override=True`.
The default in `${NAME:-default}` applies only when `NAME` is unset. Unquoted `$NAME`
without braces is literal.

Anything else raises `DotenvError` with the file and line, never the value:
multi-line quoted values, other `${...}` forms (`${X-d}`, `${X:?err}`, nesting), text
after a closing quote, and `${` inside single quotes (python-dotenv expands it, docker
compose keeps it literal). Docker compose `env_file` also expands unbraced `$NAME`
and treats `${NAME:-default}` as "unset or empty", so files that rely on those
compose-only behaviours read differently there.

## Command line

```
typedenv check env.spec                     validate every variable in a spec file
typedenv check myapp.settings:Settings      validate the fields of a dataclass
typedenv check env.spec --env-file .env     layer a .env file under the environment
typedenv check env.spec --format json       machine-readable report
typedenv get PORT --type int --default 8080 print one parsed value
typedenv get DEBUG --type bool              prints true or false
```

A spec file lists one variable per line as `NAME TYPE [optional] [secret]`, with types
`str int float bool decimal path duration json secret`, `list[:SEP]` and
`choice:A,B,C`:

```
# deployment contract
DATABASE_URL  secret
PORT          int       optional
LOG_LEVEL     choice:debug,info,warning
HOSTS         list:;
```

```
$ typedenv check env.spec
ok       DATABASE_URL  secret
invalid  PORT          int, optional: not a valid integer: 'eighty'
missing  LOG_LEVEL     choice: not set
ok       HOSTS         list
typedenv: 2 of 4 variables failed
```

`check` exits 0 when every variable is valid and 1 otherwise, so it gates a deploy
script directly. Values are printed only with `--show-values`, and secrets never are.
`--prefix`, `--env-file` and `--empty-is-unset` work on both commands; `--quiet` gives
an exit code only. Errors go to stderr with exit code 1. `python -m typedenv` works the same
as the `typedenv` script.

## Errors

`MissingEnvError` is also a `KeyError`; `InvalidEnvError`, `EnvValidationError` and
`DotenvError` are also `ValueError`s; all of them derive from `EnvError`.

## Why

Reading config from the environment is a one-liner until you want the value typed, a
missing variable to fail loudly, every failure reported in one go, secrets kept out of
logs, and your type checker to agree with all of it. The existing options each give up
one of those or pull in dependencies: `environs` needs `marshmallow` and
`python-dotenv`, `environ-config` is built on `attrs`, `pydantic-settings` pulls in
`pydantic-core`, and `typenv` depends on `python-dotenv` and has not shipped since 2021.

`typedenv` has no runtime dependencies, ships `py.typed`, and uses `@overload` so
`env.int("X")` is `int` and `env.int("X", None)` is `int | None` with no casts. Reach
for it when you want typed environment access and a deploy-time check without adding a
settings framework to the project.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
