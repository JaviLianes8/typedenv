"""The ``typedenv`` command: validate a spec against the environment, or read one value."""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from collections import ChainMap
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

from ._check import VarSpec, evaluate, evaluate_one
from ._dotenv import read_layer
from ._env import Env
from ._errors import EnvError
from ._reader import parse_value
from ._report import canonical, render_json, render_text, summary
from ._settings import specs_for
from ._specfile import TYPE_HELP, SpecError, parse_type, read_spec
from ._version import __version__

EPILOG = """\
examples:
  typedenv check env.spec                     validate every variable in a spec file
  typedenv check myapp.settings:Settings      validate the fields of a dataclass
  typedenv check env.spec --env-file .env     layer a .env file under the environment
  typedenv check env.spec --format json       machine-readable report
  typedenv get PORT --type int --default 8080 print one parsed value
  typedenv get DEBUG --type bool              prints true or false

spec file format (one variable per line, # starts a comment):
  DATABASE_URL  secret
  PORT          int       optional
  DEBUG         bool      optional
  LOG_LEVEL     choice:debug,info,warning
  HOSTS         list:;

check exits 0 when every variable is valid and 1 otherwise; values are only printed
with --show-values, and secrets never are. Errors go to stderr with exit code 1.
module:Class is imported with the current directory added to the import path.
"""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prefix", default="", help="prepend PREFIX to every name")
    parser.add_argument("--env-file", metavar="FILE", help="read FILE under the environment")
    parser.add_argument(
        "--empty-is-unset", action="store_true", help="treat variables set to '' as unset"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="typedenv",
        description="Validate and read typed environment variables.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"typedenv {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    check = commands.add_parser(
        "check",
        help="validate a spec or dataclass",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    check.add_argument("target", help="a spec file path, or module:Class for a dataclass")
    _common(check)
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.add_argument("--show-values", action="store_true", help="print values (not secrets)")
    check.add_argument("--quiet", "-q", action="store_true", help="print nothing, exit code only")
    get = commands.add_parser(
        "get",
        help="print one parsed value",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    get.add_argument("name", help="the variable name (without --prefix)")
    get.add_argument("--type", default="str", help=f"one of {TYPE_HELP} (default str)")
    get.add_argument("--default", help="value to use when the variable is unset")
    get.add_argument("--secret", action="store_true", help="never show the value in errors")
    _common(get)
    return parser


def _reader(args: argparse.Namespace) -> Env:
    source: Mapping[str, str] = os.environ
    if args.env_file:
        source = ChainMap(os.environ, read_layer(args.env_file))
    return Env(source, prefix=args.prefix, empty_is_unset=args.empty_is_unset)


def _specs(target: str) -> list[VarSpec]:
    if Path(target).is_file():
        return read_spec(target)
    module_name, colon, attr = target.partition(":")
    if not colon or not module_name or not attr:
        raise SpecError(f"{target!r} is neither a spec file nor module:Class")
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())
    obj: Any = importlib.import_module(module_name)
    for part in attr.split("."):
        obj = getattr(obj, part)
    return specs_for(obj)


def _check(args: argparse.Namespace) -> int:
    outcomes = evaluate(_specs(args.target), _reader(args))
    failed = any(outcome.failed for outcome in outcomes)
    if not args.quiet:
        render = render_json if args.format == "json" else render_text
        report = render(outcomes, args.show_values)
        if report:
            print(report)
        if args.format == "text":
            print(f"typedenv: {summary(outcomes)}", file=sys.stderr if failed else sys.stdout)
    return 1 if failed else 0


def _get(args: argparse.Namespace) -> int:
    parser, type_name = parse_type(args.type)
    spec = VarSpec(args.name, type_name, parser, required=args.default is None, secret=args.secret)
    outcome = evaluate_one(spec, _reader(args))
    if outcome.error is not None:
        raise outcome.error
    value = outcome.value
    if outcome.status == "unset":
        value = parse_value(parser, f"--default for {outcome.full_name}", args.default, args.secret)
    print("\n".join(value) if isinstance(value, list) else canonical(value))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface and return the process exit code."""
    args = build_parser().parse_args(argv)
    try:
        return _check(args) if args.command == "check" else _get(args)
    except (EnvError, SpecError, TypeError, ImportError, AttributeError, OSError) as exc:
        print(f"typedenv: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
