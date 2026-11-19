"""Conformance tests for docs/spec/types.md."""

import pytest

from .support import accepted, compile_error, same_meaning

rule = pytest.mark.rule
UNIT = pytest.mark.xfail(strict=True, reason="mtp-vc5g: unit is declared in the file types")
EASE = pytest.mark.xfail(strict=True, reason="mtp-6kta: ease is not a type")
BEZIER = pytest.mark.xfail(strict=True, reason="mtp-qnws: the shape bezier is named curve")


@rule("type-notation")
class TestTypeNotation:
    def test_a_declared_type(self):
        compile_error("(type pos real (>= 0)) (pos k -1)")
        a = accepted("(type pos real (>= 0)) (pos k 1)").get("k").value.type
        b = accepted("((real (>= 0)) k 1)").get("k").value.type
        assert (a.base, a.constraints) == (b.base, b.constraints)


@rule("the-types")
class TestTheTypes:
    def test_the_type_colormap(self):
        same_meaning(
            "(func f ((colormap m)) (m 0.5)) (colormap cm ['red' 'blue']) (color v (f cm))",
            "(func f ((func[real color] m)) (m 0.5)) (colormap cm ['red' 'blue']) (color v (f cm))",
        )

    @UNIT
    def test_unit_is_a_built_in_type(self):
        compile_error("(unit k 2)")
        accepted("(unit k 0.5)")

    @EASE
    def test_ease_is_a_built_in_type(self):
        accepted("(ease e (fn ((unit t)) t))")

    @BEZIER
    def test_bezier_is_a_shape_type(self):
        accepted("(scene s (bezier b (from [0 0]) (to [1 1])))")

    @BEZIER
    def test_curve_is_a_built_in_type(self):
        accepted("(curve c (fn ((real t)) [t t]))")


@rule("what-a-type-is")
class TestWhatATypeIs:
    def test_a_value_outside_the_set_is_an_error(self):
        compile_error("((real (>= 0)) k -1)")
        accepted("((real (>= 0)) k 1)")
