"""Conformance tests for docs/spec/data-model.md."""

import pytest

from .support import accepted, compile_error

rule = pytest.mark.rule
UNNAMED = pytest.mark.xfail(strict=True, reason="mtp-1s8z: a variable with no name compiles")


@rule("values")
class TestValues:
    def test_equal_values_are_the_same_value(self):
        m = accepted("(real v (+ 1 2) (const)) (real w 3 (const))")
        assert m.get("v").value.value == m.get("w").value.value == 3


@rule("variables")
class TestVariables:
    def test_a_bound_variable_follows_its_expression(self):
        m = accepted("(real a 1) (real b (* 2 a))")
        assert m.get("b").value.bound

    @UNNAMED
    def test_a_variable_with_no_name_is_an_error(self):
        compile_error("(real_ 1)")


@rule("objects")
class TestObjects:
    def test_two_circles_with_the_same_attributes_are_two_objects(self):
        m = accepted("(scene s (circle a (r 1)) (circle b (r 1)))")
        assert m.id("a") != m.id("b")


@rule("namespaces")
class TestNamespaces:
    def test_a_namespace_holds_the_attributes_it_is_declared_with(self):
        m = accepted("(namespace style (real width 2)) (real v style.width)")
        assert (m.id("style.width"), None) in m.get("v").value.deps
