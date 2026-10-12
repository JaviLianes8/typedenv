# typedenv improvement round

A ranked list of substantial, coherent improvements for this round. Every item is
additive: the 0.1 API (`Env`, `env`, the `str`/`int`/`float`/`bool`/`list`/`json`
getters, `EnvError`, `MissingEnvError`, `InvalidEnvError`) keeps its signatures, and
code written against 0.1 keeps working.

## Starting point

0.1 read one variable at a time with six overloaded getters, so `env.int("PORT")` was
`int` and `env.int("PORT", None)` was `int | None`. It stopped at the first problem,
quoted every bad value in its errors (secrets included), had no way to scope names,
no richer types, no settings object, no `.env` support and nothing to run from a
deployment script.

## Ranked improvements

1. **Collect every error at once.** Deployments fail one variable at a time when a
   reader stops at the first problem. `load()` reads every field first and raises one
   `EnvValidationError` whose `errors` tuple and message list every missing and invalid
   variable together.

2. **A declarative settings class without metaclass magic.** `load(Settings)` fills a
   plain (optionally frozen) dataclass: the field name upper-cased is the variable name,
   the annotation picks the parser, a default or `X | None` makes it optional.
   `var(name, default=, default_factory=, separator=, secret=)` is a drop-in for
   `field()` when a field needs more. No base class, no decorator, no metaclass.

3. **Secrets never leak.** A `secret=True` keyword on every getter keeps the value out
   of the message, the `value` attribute and the exception chain (no `__cause__` or
   `__context__` that would print it in a traceback). A `Secret` type, returned by
   `env.secret()` and usable as a field annotation, masks itself in `str`, `repr`,
   f-strings and dataclass reprs, compares in constant time, and refuses pickling.

4. **Richer typed getters with precise overloads.** `decimal` (exact, finite only),
   `path`, `duration` (`90`, `250ms`, `1h30m`, `1.5h` into `timedelta`), `enum` (member
   by name in any case, or by value) and `secret`, each with the same five overloads as
   the 0.1 getters so the static type follows the default and `required=`.

5. **Settings field types beyond scalars.** `list[X]` and `tuple[X, ...]` with a
   per-field separator and typed items, `Literal["a", "b"]` choices, `Enum`
   subclasses, `dict[...]` as a JSON object, `Secret`, plus every scalar getter type.
   An annotation that cannot come from a string fails fast with `TypeError`.

6. **Prefix scoping.** `Env(prefix="APP_")` and `env.prefixed("DB_")` read
   `APP_DB_HOST` from `host`; errors name the full variable, and `load()` honours the
   reader's prefix.

7. **A deployment checker CLI.** `typedenv check env.spec` (or `module:Class` for a
   dataclass) validates the current environment and prints one line per variable,
   exits 0 or 1, supports `--format json`, `--prefix`, `--env-file`,
   `--empty-is-unset`, `--quiet` and `--show-values` (secrets stay masked).
   `typedenv get NAME --type int --default 8080` prints one canonical value for shell
   scripts. Errors go to stderr with exit code 1.

8. **`.env` loading as a documented subset.** `parse_dotenv`, `read_dotenv` and
   `load_dotenv` implement a subset of python-dotenv 1.x syntax and are tested line by
   line against python-dotenv itself. Constructs the two common references
   (python-dotenv and docker compose `env_file`) read differently, and anything outside
   the subset, raise `DotenvError` naming the line instead of being guessed at.

9. **Platform facts made explicit.** Empty versus unset is now a choice
   (`empty_is_unset=True`), `raw()` and `is_set()` expose presence, case sensitivity
   follows the platform (documented and tested in real child processes), and
   `load_dotenv` refuses an entry Windows cannot store (`NAME=value` over 32,767
   characters) before writing anything.

10. **Boolean vocabulary aligned with boolish.** `bool` now also accepts
    `enable`/`enabled` and `disable`/`disabled`, matching the default vocabulary of the
    sibling library without depending on it.

11. **Error quality.** `MissingEnvError` no longer prints with doubled quotes, very
    long values are trimmed in messages (the attribute keeps them whole), JSON errors
    report line and column, and enum errors list the valid members.

12. **Ground-truth tests.** A contract test pins the complete promise of every public
    name; real-process tests run child interpreters with a crafted `env=`; an end to end
    test builds the wheel, installs it into a throwaway virtual environment and drives
    the installed `typedenv` script.

## Deliberately left out

- Interpolation forms beyond `${NAME}` and `${NAME:-default}`, and multi-line quoted
  `.env` values: the references disagree or the cost outweighs the use.
- ISO 8601 durations: the unit form covers configuration values without a parser for
  a second grammar.
- `~` and variable expansion in paths: a config path should mean exactly what it says.
