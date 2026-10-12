"""The .env subset, checked line by line against python-dotenv as the reference."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pytest

from typedenv import DotenvError, load_dotenv, parse_dotenv, read_dotenv

# Every line here is inside the documented subset, so typedenv must agree exactly with
# python-dotenv's dotenv_values on it (bare names, which python-dotenv maps to None,
# are dropped from both sides).
CORPUS = [
    "A=plain value  # trailing comment",
    "export B=exported",
    "export  C=1",
    "C='single $A \\n # not a comment'",
    'D="double ${A} \\n \\t \\" end"',
    "E=",
    "F",
    "G = spaced",
    "H=x#y",
    "I=${MISSING:-fallback}",
    'J="a" # comment',
    "K=$A",
    "N=  lead",
    "C= #x",
    "C='a\\'b'",
    'C="a\\nb\\\\c\\\'d\\$e"',
    "A=1\nC=${A}",
    'A=1\nC="${A}"',
    "C=a\tb",
    "C=\\${A}",
    "# only a comment",
    "   # indented comment",
    "C='x' # comment",
    "C=a b c",
    "C==x",
    "C=x=y",
    'C=""',
    "C=''",
    "C=${A:-}",
    "A=1\nA=2",
    "C=a\\nb",
    "C=${A}${A}",
    "C=a #b #c",
    "C=a\r\nD=b",
    "C=café",
    "export=1",
    "C=${A:-x y}",
    'C="a\\tb"',
    'C="a\'b"',
    "C='a\"b'",
    "C=\\\\",
    'C="\\\\"',
    "C='\\\\'",
    "A=outer\nB=${A}-${A:-no}",
]


@pytest.mark.parametrize("text", CORPUS)
def test_matches_python_dotenv(text: str) -> None:
    dotenv = pytest.importorskip("dotenv")
    expected = {
        key: value
        for key, value in dotenv.dotenv_values(stream=io.StringIO(text)).items()
        if value is not None
    }
    assert parse_dotenv(text, environ={}) == expected


@pytest.mark.parametrize(
    ("text", "line"),
    [
        ('A="unterminated', 1),
        ("A=1\nB='open", 2),
        ("A='x' trailing", 1),
        ("A='${B}'", 1),
        ("A=${B", 1),
        ("A=${B-d}", 1),
        ("A=${B:?err}", 1),
        ("A=${1X}", 1),
        ("A=${B:-${C}}", 1),
        ("'quoted'=1", 1),
    ],
)
def test_outside_the_subset_raises_naming_the_line(text: str, line: int) -> None:
    with pytest.raises(DotenvError) as info:
        parse_dotenv(text, environ={})
    assert info.value.line == line
    assert f"line {line}" in str(info.value)


def test_errors_never_quote_the_value() -> None:
    with pytest.raises(DotenvError) as info:
        parse_dotenv('TOKEN="hunter2', environ={})
    assert "hunter2" not in str(info.value)


def test_expansion_falls_back_to_the_environment() -> None:
    assert parse_dotenv("A=${HOME_X}", environ={"HOME_X": "/h"}) == {"A": "/h"}
    assert parse_dotenv("HOME_X=f\nA=${HOME_X}", environ={"HOME_X": "/h"})["A"] == "f"


def test_default_applies_only_when_unset() -> None:
    assert parse_dotenv("A=${E:-d}", environ={"E": ""}) == {"A": ""}


def test_read_dotenv_names_the_file(tmp_path: Path) -> None:
    good = tmp_path / ".env"
    good.write_text("﻿A=1\n", encoding="utf-8")
    assert read_dotenv(good, environ={}) == {"A": "1"}
    bad = tmp_path / "bad.env"
    bad.write_text("A=1\nB='x\n", encoding="utf-8")
    with pytest.raises(DotenvError) as info:
        read_dotenv(bad, environ={})
    assert info.value.path == str(bad)
    assert str(info.value).startswith(f"{bad}:2:")


def test_load_dotenv_keeps_existing_variables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / ".env"
    path.write_text("TDE_KEEP=file\nTDE_NEW=${TDE_KEEP}\n", encoding="utf-8")
    monkeypatch.setenv("TDE_KEEP", "env")
    monkeypatch.delenv("TDE_NEW", raising=False)
    assert load_dotenv(path) == {"TDE_NEW": "env"}
    assert os.environ["TDE_KEEP"] == "env"
    assert os.environ["TDE_NEW"] == "env"


def test_load_dotenv_override_lets_the_file_win(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / ".env"
    path.write_text("TDE_KEEP=file\nTDE_NEW=${TDE_KEEP}\n", encoding="utf-8")
    monkeypatch.setenv("TDE_KEEP", "env")
    monkeypatch.setenv("TDE_NEW", "old")
    assert load_dotenv(path, override=True) == {"TDE_KEEP": "file", "TDE_NEW": "file"}
    assert os.environ["TDE_NEW"] == "file"


@pytest.mark.skipif(sys.platform != "win32", reason="the 32,767 limit is a Windows rule")
def test_load_dotenv_refuses_entries_windows_cannot_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TDE_BIG", raising=False)
    monkeypatch.delenv("TDE_OK", raising=False)
    path = tmp_path / ".env"
    path.write_text("TDE_OK=1\nTDE_BIG=" + "x" * 32767 + "\n", encoding="utf-8")
    with pytest.raises(DotenvError) as info:
        load_dotenv(path)
    assert info.value.line == 2
    assert "TDE_OK" not in os.environ
    fits = "x" * (32767 - len("TDE_BIG="))
    path.write_text(f"TDE_BIG={fits}\n", encoding="utf-8")
    assert load_dotenv(path) == {"TDE_BIG": fits}
