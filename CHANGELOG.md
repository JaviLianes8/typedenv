# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

### Added

- `load(cls, source=None)` fills a plain dataclass from the environment: field name
  upper-cased as the variable name, the annotation as the parser, a default,
  `default_factory` or `X | None` making it optional. Every field is read first and all
  failures are raised together as `EnvValidationError` (its `errors` tuple holds each one).
- `var(name, default=, default_factory=, separator=, secret=)`, a `field()` replacement
  for fields that need a different name, a list separator or masking.
- Settings fields may be `str`, `int`, `float`, `bool`, `Decimal`, `Path`, `timedelta`,
  `Secret`, any `Enum`, `Literal[...]` of strings, `dict[...]` (a JSON object), and
  `list[X]` / `tuple[X, ...]` of a scalar type.
- New getters, each with the same typed overloads as the 0.1 ones: `decimal` (finite
  only), `path`, `duration` (`90`, `250ms`, `1h30m`, `1.5h` into `timedelta`), `enum`
  (member name in any case, or value) and `secret`.
- `secret=True` on every getter keeps the value out of the error message, its `value`
  attribute and the exception chain. `Secret` masks itself in `str`, `repr` and
  f-strings, compares in constant time and refuses pickling.
- `Env(prefix=...)` and `Env.prefixed()` scope names; errors name the full variable.
- `Env(empty_is_unset=True)` treats `KEY=` as unset; `Env.raw()`, `Env.is_set()`,
  `in`, `Env.source`, `Env.full_name()` and a repr that never shows values.
- `.env` support as a documented subset of python-dotenv 1.x: `parse_dotenv`,
  `read_dotenv` and `load_dotenv(path, override=False)`, raising `DotenvError` (file and
  line, never the value) for anything outside the subset. On Windows, `load_dotenv`
  refuses entries longer than the 32,767 characters the process environment accepts.
- `typedenv` command (also `python -m typedenv`): `check` validates a spec file or a
  `module:Class` dataclass against the environment with text or JSON output, and `get`
  prints one parsed value. Both take `--prefix`, `--env-file` and `--empty-is-unset`.
- `InvalidEnvError` gains `reason`, `secret`, `detail` and `masked()`.

### Changed

- `bool` also accepts `enable`/`enabled` and `disable`/`disabled`, matching boolish.
- Very long values are trimmed in error messages; the `value` attribute keeps them whole.
- JSON errors report the line and column.

### Fixed

- `str(MissingEnvError(...))` no longer wraps the message in an extra pair of quotes.

## [0.1.0]

### Added

- `Env` reader and a module-level `env` default, backed by `os.environ` or any mapping
  you pass to `Env(source=...)`.
- Typed getters `str`, `int`, `float`, `bool`, `list` and `json`, each overloaded so the
  return type follows the call: non-optional when required, `T | None` with a `None`
  default or `required=False`.
- `bool` accepts `true/false`, `yes/no`, `on/off` and `1/0` in any case; `list` splits on
  a configurable separator; `json` parses with the standard library.
- `MissingEnvError` (also a `KeyError`) and `InvalidEnvError` (also a `ValueError`), both
  naming the offending variable.
- Ships `py.typed`, no runtime dependencies.
