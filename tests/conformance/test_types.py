"""Conformance tests for docs/spec/types.md."""

import pytest

from .support import accepted, compile_error, same_meaning

rule = pytest.mark.rule
UNIT = pytest.mark.xfail(strict=True, reason="mtp-vc5g: unit is declared in the file types")
EASE = pytest.mark.xfail(strict=True, reason="mtp-6kta: ease is not a type")
UNION = pytest.mark.xfail(strict=True, reason="mtp-mo3r: a type joins only with none")
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
            "(func f ((colormap m)) (m 0.5)) (colormap cm {#'red' #'blue'}) (color v (f cm))",
            "(func f ((func[real color] m)) (m 0.5)) (colormap cm {#'red' #'blue'})"
            " (color v (f cm))",
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

    @UNION
    def test_a_union_of_two_types(self):
        accepted("(func f ((point|circle p)) 1)")

    @UNION
    def test_a_variable_whose_type_is_an_interface(self):
        accepted("(interface inky (color ink)) (namespace day (color ink #'navy')) (inky look day)")


TYPES_REDESIGN = pytest.mark.xfail(
    strict=True, reason="mtp-rk1i: the type calculus is not in the compiler"
)


@rule("membership")
class TestMembership:
    @TYPES_REDESIGN
    def test_is_narrows_a_union(self):
        accepted("(func size ((point|circle p)) (if (is p circle) p.r 0))")


@rule("modular-types")
class TestModularTypes:
    @TYPES_REDESIGN
    def test_a_modular_type_brings_a_value_in(self):
        m = accepted("((mod real 0 360) theta 400 (const))")
        assert m.get("theta").value.value == 40

    @TYPES_REDESIGN
    def test_a_modular_type_takes_no_comparison(self):
        accepted("((mod real 0 360) theta 10)")
        compile_error("((mod real 0 360) theta 10) (bool v (< theta 90))")


def xfail(bead: str | None, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}" if bead else why)


TYPE_FORMS = xfail(None, "the compiler does not read (type-apply ...) written out")
DEFAULT_UPPER = xfail(None, "a type that holds only (<= c) has no default value")
COLOR_OF = xfail("mtp-ivdt", "there is no color-of")
KNOWN_IF = xfail(None, "an if whose branches have one known length has no known length")
CHOICES = xfail("mtp-ydd4.7.42", "the choices are checked only for a value known when compiling")
MOVEMENT_INTERFACES = xfail(None, "zero-duration and instant are not types")
VARIANT_PARAMETER = xfail("mtp-ydd4.7.61", "a variant parameter that its shape does not read")
FUNCTION_VALUES = xfail("mtp-ydd4.7.43", "a list of functions and a function result that is one")
RECURSION = xfail("mtp-127y", "a function that calls itself may leave out its result type")

FACTORIAL = "((int n)) (if (= n 0) 1 (* n (f (- n 1)))))"


@rule("type-forms")
class TestTypeForms:
    def test_list_and_func_take_types_in_brackets(self):
        assert accepted("(list[int] v {1 2})").get("v").value.value == [1, 2]
        accepted("(func f ((func[real real] h)) (h 1)) (real v (f sind))")

    @pytest.mark.parametrize("src", ["(real[int] v 1)", "(list[int real] v {1})"])
    def test_other_types_in_brackets_are_an_error(self, src):
        compile_error(src)

    def test_list_with_no_item_type_takes_the_type_of_its_value(self):
        same_meaning("(list v {1 2})", "(list[int] v {1 2})")

    @pytest.mark.parametrize("src", ["(list v)", "(func f ((list xs)) 1)"])
    def test_list_with_no_item_type_and_no_value(self, src):
        compile_error(src)

    @UNION
    def test_a_union_of_a_type_with_itself(self):
        same_meaning("(real|real v 1)", "(real v 1)")

    @TYPE_FORMS
    def test_the_type_forms_written_out(self):
        same_meaning("((type-apply list int) v {1 2})", "(list[int] v {1 2})")


@rule("subtypes")
class TestSubtypes:
    @pytest.mark.parametrize(
        "src",
        [
            "(func f ((real|none x)) 1) (real v (f 2))",
            "(func f ((list[real] xs)) 1) (real v (f {1 2}))",
            "(int n 1) (real v n)",
            "((real (>= 0)) a 2) ((real (>= -1)) v a)",
            "((int (> 0)) a 2) ((int (>= 1)) v a)",
            "(type u real (>= 0) (<= 1)) (func g ((func[u real] h)) (h 0.5))"
            " (func twice ((real x)) (* 2 x)) (real v (g twice))",
        ],
    )
    def test_a_subtype_is_accepted(self, src):
        accepted(src)

    @pytest.mark.parametrize(
        "src",
        [
            "(string s 'a') (real v s)",
            "((real (>= -1)) a 2) ((real (>= 0)) v a)",
            "(type u real (>= 0) (<= 1)) (func g ((func[real real] h)) (h 0.5))"
            " (func twice ((u x)) (* 2 x)) (real v (g twice))",
        ],
    )
    def test_a_type_that_is_not_a_subtype_is_an_error(self, src):
        compile_error(src)

    @TYPES_REDESIGN
    def test_a_modular_type_is_not_a_subtype_of_real(self):
        accepted("((mod real 0 360) theta 10)")
        compile_error("((mod real 0 360) theta 10) (real v theta)")


@rule("constraints")
class TestConstraints:
    def test_the_conditions(self):
        accepted("(real k 1 (>= 0) (< 2))")
        accepted("(list[int] xs {1 2} (length 2))")
        accepted("(string s 'a' (one-of 'a' 'b'))")

    @TYPES_REDESIGN
    @pytest.mark.parametrize(
        "src",
        ["(string s 'ab' (length 2))", "(int n 1 (one-of 1 2))", "(bool b true (one-of true))"],
    )
    def test_length_on_strings_and_one_of_on_other_types(self, src):
        accepted(src)

    @pytest.mark.parametrize(
        "src",
        [
            "(bool b true (>= 0))",
            "(string s 'a' (>= 0))",
            "(real k 1 (length 2))",
            "(real k 1 (foo 2))",
            "(func f (((circle (>= 0)) c)) 1)",
            "(real a 1) (real k 1 (>= a))",
            "(list[int] xs {} (length -1))",
        ],
    )
    def test_any_other_condition_is_an_error(self, src):
        compile_error(src)

    @TYPES_REDESIGN
    @pytest.mark.parametrize("src", ["((real (const)) k 1)", "((real (wrap 0 360)) k 1)"])
    def test_const_and_wrap_are_not_conditions(self, src):
        compile_error(src)


@rule("type-values")
class TestTypeValues:
    @pytest.mark.parametrize(
        "src, expected",
        [
            ("(real v)", 0),
            ("(int v)", 0),
            ("(ratio v)", 0),
            ("(complex v)", 0),
            ("(real v (>= 1))", 1),
            ("(bool v)", False),
            ("(string v)", ""),
            ("(point v)", (0, 0)),
            ("(list[int] v)", []),
            ("(list[int] v (length 2))", [0, 0]),
            ("(real|none v)", None),
            ("(string v (one-of 'b' 'a'))", "b"),
            ("(func f ((real x) (real y)) y) (real v (f 1))", 0),
        ],
    )
    def test_the_default_value_of_a_type(self, src, expected):
        assert accepted(src).get("v").value.value == expected

    def test_the_default_color_is_black(self):
        same_meaning("(color v)", "(color v #'#000000')")

    @DEFAULT_UPPER
    def test_a_type_that_holds_only_an_upper_bound(self):
        assert accepted("(real v (<= -1))").get("v").value.value == -1

    @TYPES_REDESIGN
    def test_the_first_choice_that_meets_the_other_conditions(self):
        assert accepted("((int (one-of 5 1) (<= 3)) v)").get("v").value.value == 1

    @pytest.mark.parametrize(
        "src", ["(real v (> 1))", "(motif m ((circle c)) (circle_ (r 1))) (scene s (m a))"]
    )
    def test_leaving_out_a_value_of_a_type_with_no_default_is_an_error(self, src):
        compile_error(src)


@rule("conversions")
class TestConversions:
    @pytest.mark.parametrize(
        "src", ["(string s 'red') (scene sc (circle d (fill s)))", "(int v 2.5)", "(string v 3)"]
    )
    def test_no_value_changes_type_by_itself(self, src):
        compile_error(src)

    def test_a_form_that_asks_for_it(self):
        accepted("(int v (round 2.5))")

    @COLOR_OF
    def test_color_of(self):
        accepted("(string s 'red') (scene sc (circle d (fill (color-of s))))")


@rule("known-lengths")
class TestKnownLengths:
    @pytest.mark.parametrize(
        "src",
        [
            "(real a 1) (real v (. {a 0 1} 1))",
            "(list[real] xs {1 2 3} (length 3)) (real v (. xs 1))",
            "(real a 1) (list[real] xs {a 0 1}) (real v (. xs 1))",
            "(func f ((real a)) {a a}) (real b 1) (real v (. (f b) 1))",
            "(scene s (group g (circle c1 (r 1)) (circle c2 (r 2)))) (real v (. g.r 1))",
            "(real a 1) (list[list[real]] xs {{a 1} {2 a}}) (real v (. (. xs 0) 1))",
        ],
    )
    def test_an_item_of_a_list_of_known_length_is_never_none(self, src):
        accepted(src)

    def test_a_free_list_declared_with_no_length(self):
        compile_error("(list[real] xs {1 2 3}) (real v (. xs 1))")

    @KNOWN_IF
    def test_an_if_whose_branches_have_the_same_known_length(self):
        accepted("(bool c true) (real a 1) (real v (. (if c {a 1} {2 a}) 1))")


@rule("none-only-where-allowed")
class TestNoneOnlyWhereAllowed:
    SECANT = "(real theta 90) (real|none s (secd theta)) "
    NONE = "(real|none r none) "

    def test_an_argument_of_a_call(self):
        accepted(self.SECANT + "(real|none v (* 2 s))")
        compile_error(self.SECANT + "(real v (* 2 s))")

    def test_an_attribute_of_a_shape_declared_with_none(self):
        accepted(self.NONE + "(scene s (circle|none c (pos [0 0]) (r r)))")
        compile_error(self.NONE + "(scene s (circle k (pos [0 0]) (r r)))")

    @pytest.mark.parametrize("src", [NONE + "(real v r)", "(bool|none c none) (real v (if c 1 2))"])
    def test_nowhere_else(self, src):
        compile_error(src)


@rule("choice-types")
class TestChoiceTypes:
    SIDE = "(type side string (one-of 'left' 'right')) "

    def test_a_choice(self):
        accepted(self.SIDE + "(side v 'left')")

    def test_a_value_that_is_not_a_choice(self):
        compile_error(self.SIDE + "(side v 'up')")

    @CHOICES
    def test_a_free_string_is_not_proved_to_be_a_choice(self):
        compile_error(self.SIDE + "(string q 'left') (side v q)")


@rule("interfaces")
class TestInterfaces:
    def test_positioned_takes_points_and_shapes(self):
        src = "(func label-at ((positioned o)) o.x) "
        accepted(src + "(point p [1 2]) (real v (label-at p))")
        accepted(src + "(scene s (circle c (r 1) (x 3))) (real v (label-at c))")

    def test_a_value_is_read_only_through_the_attributes_of_its_interface(self):
        compile_error("(func f ((positioned o)) o.r)")

    def test_a_declared_interface(self):
        accepted(
            "(interface radial (real r)) (func area ((radial o)) (* pi o.r o.r))"
            " (motif dot ((real r 0.5 (>= 0))) (circle face (r r)))"
            " (scene s (circle c (r 1)) (dot d (r 0.5))) (real v (area c)) (real w (area d))"
        )

    def test_an_attribute_must_be_of_a_subtype_of_the_listed_type(self):
        src = "(namespace rec (real r 1)) (func f ((radial o)) o.r) (real v (f rec))"
        accepted("(interface radial (real r)) " + src)
        compile_error("(interface radial (real r (>= 0))) " + src)

    @MOVEMENT_INTERFACES
    def test_zero_duration_and_instant(self):
        accepted("(func f ((zero-duration m) (instant n)) 1)")


@rule("motif-and-variant-types")
class TestMotifAndVariantTypes:
    BAR = "(variant bar ((real p 0)) (rect_ (width 0.8) (height (* 5 p)))) "
    M = "(motif m () (circle_ (r 1))) "

    def test_a_variant_is_a_subtype_of_the_type_of_its_shape(self):
        accepted(
            self.BAR + "(func area ((rect q)) (* q.width q.height))"
            " (scene s (bar b1 (p 1))) (real v (area b1))"
        )

    @pytest.mark.parametrize("attr", ["width", "height"])
    def test_a_variant_may_not_set_an_attribute_that_its_shape_sets(self, attr):
        compile_error(self.BAR + f"(scene s (bar b2 ({attr} 2)))")

    def test_a_parameter_named_like_an_attribute(self):
        compile_error("(variant bar ((real width 1)) (rect_ (width width) (height 1)))")

    @VARIANT_PARAMETER
    def test_a_parameter_that_the_shape_does_not_read(self):
        compile_error("(variant bar ((real p 0) (real q 1)) (rect_ (width 0.8) (height (* 5 p))))")

    def test_a_motif_type_is_disjoint_from_every_other_type(self):
        accepted(self.M + "(func f ((m c)) 1) (scene s (m a)) (real v (f a))")
        compile_error(self.M + "(func f ((circle c)) 1) (scene s (m a)) (real v (f a))")
        compile_error(self.M + "(func f ((m c)) 1) (scene s (circle b (r 1))) (real v (f b))")


@rule("function-types")
class TestFunctionTypes:
    def test_a_parameter_may_be_a_function(self):
        src = "(func twice ((func[real real] f) (real x)) (f (f x)))"
        v = accepted(src + " (real v (twice (fn ((real x)) (* 2 x)) 3))").get("v").value.value
        assert v == 12

    def test_the_type_of_fn_has_the_type_of_its_body_as_its_result(self):
        compile_error("(func g ((func[real real] h)) (h 2)) (real v (g (fn ((real x)) 'a')))")

    @FUNCTION_VALUES
    @pytest.mark.parametrize(
        "src",
        [
            "(list[func[real real]] fs {sind cosd})",
            "(list fs {sind cosd})",
            "(func g () sind)",
            "(func g () {sind cosd})",
        ],
    )
    def test_no_variable_and_no_result_holds_a_function(self, src):
        compile_error(src)


@rule("parameters")
class TestParameters:
    @pytest.mark.parametrize(
        "src",
        [
            "(func f ((real x 'a')) x)",
            "(real a 1) (func f ((real x a)) x)",
            "(func f (((real (>= 0)) x)) x) (real v (f -1))",
            "(func g ((func[real real real] h)) (h 2))",
        ],
    )
    def test_errors(self, src):
        compile_error(src)

    def test_a_parameter_left_out_holds_its_default(self):
        src = "(func f ((real x) (real y 5)) (+ x y)) (real v (f 1))"
        assert accepted(src).get("v").value.value == 6

    def test_a_parameter_with_no_default_holds_the_default_value_of_its_type(self):
        assert accepted("(func f ((real x) (real y)) y) (real v (f 1))").get("v").value.value == 0

    def test_a_bare_parameter_of_fn_takes_the_expected_type(self):
        assert accepted("(list[real] v (map {1 2} (fn x (* 2 x))))").get("v").value.value == [2, 4]


@rule("function-result-type")
class TestFunctionResultType:
    def test_a_declared_result_type(self):
        compile_error("(func[real] f ((real x)) 'a')")

    def test_the_type_of_the_body(self):
        assert accepted("(func f ((real x)) 'a') (string v (f 1))").get("v").value.value == "a"
        compile_error("(func f ((real x)) 'a') (real v (f 1))")

    def test_a_function_that_calls_itself_with_its_result_type(self):
        assert accepted("(func[int] f " + FACTORIAL + " (int v (f 4))").get("v").value.value == 24

    @RECURSION
    def test_a_function_that_calls_itself_without_its_result_type(self):
        compile_error("(func f " + FACTORIAL)


@rule("form-types")
class TestFormTypes:
    @pytest.mark.parametrize(
        "src",
        [
            "(bool on true) (int v (if on 1 2.5))",
            "(real v (as int 2.5))",
            "(list v {})",
            "(real v (type-of 3))",
            "(real a 1) (real v (= a 2))",
            "(real|none r none) (string v f'{r}')",
            "(list[int] xs {1 2}) (string|none v (. xs 0))",
        ],
    )
    def test_an_expression_whose_type_is_not_a_subtype_of_the_expected_type(self, src):
        compile_error(src)

    @pytest.mark.parametrize(
        "src",
        [
            "(int n 1) (real v n)",
            "(list[real] v (as list[real] {}))",
            "(list[real] v {})",
            "(string v (type-of 3))",
            "(real a 1) (bool v (= a 2))",
            "(func f ((real x)) (/ 1 x)) (real v (or? (f 0) 5))",
            "(real|none r none) (string|none v f'{r}')",
            "(point p [1 2]) (real v p.x)",
            "(list[int] xs {1 2}) (int|none v (. xs 0))",
            "(real a 1) (real v (free (* 2 a)))",
        ],
    )
    def test_an_expression_whose_type_is_a_subtype_of_the_expected_type(self, src):
        accepted(src)

    @COLOR_OF
    def test_color_of(self):
        accepted("(color v (color-of 'red'))")
        accepted("(string s 'red') (color|none v (color-of s))")
        compile_error("(string s 'red') (color v (color-of s))")
