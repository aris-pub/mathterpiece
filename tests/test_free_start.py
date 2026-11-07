"""free@: a free variable or attribute whose starting value an expression gives, read once when
the live model is built and never followed (docs/reference.md, "Free starting values")."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece.nodes import Form, Name
from mathterpiece.parse import ParseError, parse


def test_it_parses_as_a_form_no_author_can_write():
    (decl,) = parse("(real k free@(+ 1 2))")
    form = decl.items[2]
    assert isinstance(form, Form)
    assert isinstance(form.items[0], Name) and form.items[0].parts == ("free@",)


def test_it_is_followed_by_its_expression():
    with pytest.raises(ParseError, match="free@ is followed by the expression"):
        parse("(real k free@)")


def test_it_starts_free_from_an_expression_known_only_while_drawing():
    m = model("(real a 1) (real k free@(* 2 a))")
    k = m.get("k").value
    assert not k.bound
    assert k.start is not None


def test_one_known_when_compiling_is_free_and_not_const():
    m = model("(real k free@(+ 1 2)) (animation go (move k (to 5) (duration 1)))")
    k = m.get("k").value
    assert not k.bound and k.start is None and k.value == 3


def test_a_writer_may_write_it():
    model("(real a 1) (real k free@(* 2 a)) (animation go (move k (to 5) (duration 1)))")


def test_a_shape_attribute():
    m = model("(real a 1 (>= 0)) (scene s (circle c (r free@(* 2 a))))")
    assert m.get("c").attrs["r"].start is not None


def test_it_is_written_with_its_start_and_what_it_reads():
    d = doc("(real a 1) (real k free@(* 2 a))")
    k = d["objects"][d["names"]["k"]]["value"]
    assert "start" in k and "free" not in k and "bound" not in k
    assert k["deps"] == [[d["names"]["a"], None]]
    assert errors(d) == []


def test_only_as_a_value():
    error("(real a 1) (real k (+ 1 free@(* 2 a)))", "free@ gives a variable or an attribute")


def test_not_on_a_const_variable():
    error("(real a 1) (real k free@(* 2 a) (const))", "a const variable cannot start free@")


def test_not_on_a_token():
    error("(color a '#ff0000') (color k free@a)", "a color variable is a token")
