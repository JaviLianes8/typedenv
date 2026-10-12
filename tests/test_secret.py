"""The Secret wrapper hides its value everywhere except reveal()."""

from __future__ import annotations

import copy
import pickle

import pytest

from typedenv import Secret


def test_every_text_form_is_masked() -> None:
    token = Secret("hunter2")
    assert repr(token) == "Secret('***')"
    assert str(token) == "***"
    assert f"{token}" == "***"
    assert f"{token:>5}" == "  ***"
    assert "hunter2" not in repr([token, {"k": token}])


def test_reveal_returns_the_value() -> None:
    assert Secret("hunter2").reveal() == "hunter2"


def test_equality_and_hash_follow_the_value() -> None:
    assert Secret("a") == Secret("a")
    assert Secret("a") != Secret("b")
    assert Secret("a") != "a"
    assert len({Secret("a"), Secret("a")}) == 1


def test_truthiness_follows_the_value() -> None:
    assert Secret("x")
    assert not Secret("")


def test_only_strings_are_accepted() -> None:
    with pytest.raises(TypeError):
        Secret(123)  # type: ignore[arg-type]


def test_pickling_is_refused() -> None:
    with pytest.raises(TypeError):
        pickle.dumps(Secret("hunter2"))


def test_copies_are_the_same_object() -> None:
    token = Secret("hunter2")
    assert copy.copy(token) is token
    assert copy.deepcopy(token) is token


def test_attributes_cannot_be_added() -> None:
    with pytest.raises(AttributeError):
        Secret("x").extra = 1  # type: ignore[attr-defined]
