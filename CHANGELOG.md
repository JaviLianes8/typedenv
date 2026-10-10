# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
