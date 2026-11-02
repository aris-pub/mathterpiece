"""The compiler's core: declarations, names, the body rule and typed expressions (docs/syntax.md
sections 4, 8 and 9; docs/type-system.md sections 3 to 5.b)."""

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.types import BOOL, COLOR, INT, RATIO, REAL, STRING, ListT, Maybe, Refine


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


def value(src, name):
    """The folded value of a variable known when compiling."""
    place = model(src).get(name).value
    assert not place.bound, f"{name} is not known when compiling"
    return place.value


class TestVariables:
    def test_a_global_variable(self):
        m = model("(real k 1)")
        k = m.get("k")
        assert (k.kind, k.name) == ("variable", "k")
        assert k.value.type == REAL
        assert k.value.value == 1

    def test_types_from_their_head(self):
        m = model("(int n 3) (bool b true) (string s 'hi') (color c 'red') (list xs [1 2])")
        assert [m.get(x).value.type for x in "nbscx" if x != "x"] == [INT, BOOL, STRING, COLOR]
        assert m.get("xs").value.type == ListT(INT)

    def test_a_type_expression_heads_a_declaration(self):
        m = model("(list[color] p ['red' 'gold']) (real|none c none)")
        assert m.get("p").value.type == ListT(COLOR)
        assert m.get("c").value.type == Maybe(REAL)

    def test_constraints_follow_the_value(self):
        k = model("(real k 0.5 (>= 0) (<= 1))").get("k")
        assert k.value.type == Refine(REAL, ((">=", 0), ("<=", 1)))

    def test_a_value_may_be_left_out(self):
        assert value("(real k)", "k") == 0
        assert value("(real k (>= 1))", "k") == 1
        assert value("(bool b)", "b") is False
        assert value("(string s (one-of 'left' 'right'))", "s") == "left"

    def test_a_value_that_breaks_its_constraint(self):
        error("(real k 2 (<= 1))", r"2 breaks \(<= 1\)")

    def test_a_value_of_the_wrong_type(self):
        error("(real k 'a')", "expected real, got string")

    def test_named_types(self):
        m = model("(type unit real (>= 0) (<= 1)) (unit p 0.5)")
        assert str(m.get("p").value.type) == "unit"


class TestNames:
    def test_declare_before_use(self):
        error("(real a b) (real b 1)", "unknown name 'b'")

    def test_unique(self):
        error("(real k 1) (real k 2)", "'k' is already declared")

    @pytest.mark.parametrize("word", ["scene", "when", "else", "self", "const", "wait"])
    def test_reserved_words(self, word):
        error(f"(real {word} 1)", f"'{word}' is reserved")

    def test_a_name_is_bare(self):
        error("(real 'k' 1)", "a name is written bare")


class TestScene:
    def test_shapes_in_the_scene(self):
        m = model("(scene s (circle c (r 2)) (rect b))")
        s = m.get("s")
        assert s.kind == "scene"
        assert [m.objects[i].name for i in s.members] == ["c", "b"]
        assert m.get("c").attrs["r"].value == 2

    def test_variables_in_the_scene(self):
        m = model("(scene s (real k 1 (>= 0)) (circle c (r k)))")
        assert m.get("k").access == "scene"

    def test_exactly_one_scene(self):
        error("(scene s) (scene t)", "a file has exactly one scene")

    def test_shapes_only_inside_the_scene(self):
        error("(circle c)", "a shape is declared only inside the scene")

    def test_groups_hold_shapes(self):
        m = model("(scene s (group g (circle a) (circle b)))")
        assert [m.objects[i].name for i in m.get("g").members] == ["a", "b"]

    def test_anonymous(self):
        m = model("(scene s (circle _ (r 1)))")
        (c,) = [o for o in m.objects if o.kind == "circle"]
        assert c.name is None

    def test_an_unknown_argument(self):
        error("(scene s (circle c (width 2)))", "a circle takes no argument 'width'")

    def test_an_argument_given_twice(self):
        error("(scene s (circle c (r 1) (r 2)))", "'r' is given twice")

    def test_a_negative_radius(self):
        error("(scene s (circle c (r -1)))", r"-1 breaks \(>= 0\)")


class TestExpressions:
    def test_arithmetic_folds(self):
        assert value("(real k (+ 1 2 3))", "k") == 6
        assert value("(real k (* 2 (- 5 1)))", "k") == 8

    def test_division_of_ints_is_a_ratio(self):
        m = model("(ratio r (/ 1 3))")
        assert m.get("r").value.value == pytest.approx(1 / 3)
        error("(int n (/ 1 3))", "expected int, got ratio")

    def test_numbers_broaden(self):
        assert value("(real k (+ 1 0.5))", "k") == 1.5

    def test_a_known_division_by_zero(self):
        error("(real k (/ 1 0))", "division by zero")

    def test_comparisons_and_logic(self):
        assert value("(bool b (and (> 2 1) (not (= 1 2))))", "b") is True
        assert value("(bool b (or false (<= 1 1)))", "b") is True

    def test_if_and_cond(self):
        assert value("(real k (if (> 2 1) 10 20))", "k") == 10
        assert value("(string s (cond ((= 1 2) 'a') ((= 1 1) 'b') (else 'c')))", "s") == "b"

    def test_let(self):
        assert value("(real k (let ((a 2) (b (* a 3))) (+ a b)))", "k") == 8

    def test_a_condition_must_be_a_bool(self):
        error("(real k (if 1 2 3))", "expected bool, got int")

    def test_reading_a_variable(self):
        m = model("(real k 2) (real d (* 2 k))")
        d = m.get("d").value
        assert d.bound
        assert d.deps == {(m.id("k"), None)}

    def test_a_const_variable_folds(self):
        assert value("(real k 2 (const)) (real d (* 2 k))", "d") == 4

    def test_reading_an_attribute(self):
        m = model("(scene s (real k 1 (>= 0)) (circle c (r k)) (circle d (r (* 2 c.r))))")
        assert m.get("d").attrs["r"].deps >= {(m.id("c"), "r")}

    def test_an_unknown_attribute(self):
        error("(scene s (circle c) (circle d (r c.width)))", "a circle has no attribute 'width'")

    def test_strings_as_colors(self):
        m = model("(scene s (circle c (fill 'red')))")
        assert m.get("c").attrs["fill"].type == Maybe(COLOR)
        error("(scene s (circle c (fill 'blurple')))", "'blurple' is not a color")


class TestRanges:
    def test_a_variable_range_from_its_constraints(self):
        m = model("(real k 1 (>= 0) (<= 10)) (real d (* 2 k))")
        assert m.get("d").value.expr.range == (0, 20)

    def test_a_radius_proven_non_negative(self):
        model("(scene s (real k 1 (>= 0)) (circle c (r (* 2 k))))")

    def test_a_radius_not_proven(self):
        error("(scene s (real k 1) (circle c (r (* 2 k))))", r"r may break \(>= 0\)")

    def test_ratio_type(self):
        assert model("(ratio r 1/3)").get("r").value.type == RATIO
        assert model("(string s 'a')").get("s").value.type == STRING


class TestInterpolatedStrings:
    # reference.md, "Interpolated strings" and the rounding rule in "Numbers".
    def test_known_parts_fold(self):
        assert value("(string s $'{(+ 1 2)} and {2.5}')", "s") == "3 and 2.5"

    def test_a_real_shows_as_python_does(self):
        assert value("(real k 1 (const)) (string s $'{k}')", "s") == "1.0"

    def test_a_format_spec(self):
        assert value("(string s $'{2.675:.2f}')", "s") == "2.68"
        assert value("(string s $'{-2.5:.0f}')", "s") == "-3"
        assert value("(string s $'{0.125:.1%}')", "s") == "12.5%"
        assert value("(string s $'{7:03d}')", "s") == "007"
        assert value("(string s $'{1.5:>6.2f}')", "s") == "  1.50"

    def test_a_spec_that_does_not_fit_the_type(self):
        error("(string s $'{1.5:d}')", "'d' is not a format for a real")

    def test_a_part_read_while_drawing(self):
        m = model("(real k 1) (string s $'k = {k:.2f}')")
        s = m.get("s").value
        assert s.bound
        assert s.expr.op == "format"
        assert s.deps == {(m.id("k"), None)}


class TestComputedNames:
    # syntax.md, section 4: (name s).
    def test_a_name_built_from_a_string(self):
        m = model("(scene s (circle (name $'dot-{1}') (r 2)))")
        assert m.get("dot-1").attrs["r"].value == 2

    def test_referring_to_it(self):
        m = model("(scene s (circle (name 'c0') (r 2)) (circle d (r (. (name $'c{0}') r))))")
        assert m.get("d").attrs["r"].deps >= {(m.id("c0"), "r")}

    def test_the_string_must_be_known_when_compiling(self):
        error("(scene s (real k 1) (circle (name $'c{k}')))", "known when compiling")

    def test_the_built_name_follows_the_name_rules(self):
        error("(scene s (circle (name 'when')))", "'when' is reserved")
        error("(scene s (circle c) (circle (name 'c')))", "'c' is already declared")


class TestRepeat:
    # reference.md, "Special forms": (repeat n i decl…).
    def test_it_declares_n_copies(self):
        m = model("(scene s (repeat 3 i (circle (name $'dot-{i}') (r (+ i 1)))))")
        assert [m.get(f"dot-{i}").attrs["r"].value for i in range(3)] == [1, 2, 3]

    def test_the_count_must_be_known_when_compiling(self):
        assert model("(int n 2 (const)) (scene s (repeat n i (circle (name $'c{i}'))))").get("c1")
        error("(int n 2) (scene s (repeat n i (circle (name $'c{i}'))))", "known when compiling")

    def test_inside_a_group(self):
        m = model("(scene s (group g (repeat 2 i (circle (name $'m{i}')))))")
        assert [m.objects[j].name for j in m.get("g").members] == ["m0", "m1"]

    def test_a_plain_name_is_declared_twice(self):
        error("(scene s (repeat 2 i (circle c)))", "'c' is already declared")

    def test_several_declarations(self):
        m = model("(scene s (repeat 2 i (real (name $'k{i}') i) (circle (name $'c{i}'))))")
        assert m.get("k1").value.value == 1
        assert m.get("c1")


class TestParts:
    # syntax.md, section 7.
    def test_the_part_form(self):
        m = model("(scene s (circle c (r 2)) (circle d (r (. c r))))")
        assert m.get("d").attrs["r"].deps >= {(m.id("c"), "r")}
        assert value("(list xs [4 5] (const)) (real k (. xs 1))", "k") == 5

    def test_pos_is_x_and_y(self):
        m = model("(scene s (circle c (x 1) (y 2)) (circle d (pos c.pos)))")
        assert m.get("d").attrs["y"].deps >= {(m.id("c"), "y")}

    def test_a_member_by_its_name(self):
        m = model("(scene s (group g (circle a) (circle b (r 3))) (circle d (r (. (. g 'b') r))))")
        assert m.get("d").attrs["r"].deps >= {(m.id("b"), "r")}

    def test_an_unknown_attribute_in_the_part_form(self):
        src = "(scene s (circle c) (circle d (r (. c width))))"
        error(src, "a circle has no attribute 'width'")


class TestAbs:
    def test_abs(self):
        assert value("(real k (abs -2.5))", "k") == 2.5
        assert value("(int n (abs -2))", "n") == 2

    def test_its_range_is_non_negative(self):
        model("(scene s (real k 1) (circle c (r (abs k))))")


class TestEmptyForm:
    def test_an_empty_list_of_bindings(self):
        assert value("(real k (let () 3))", "k") == 3

    def test_not_a_value(self):
        error("(real k ())", r"\(\) is an empty list of parameters or bindings, not a value")


class TestTypeOf:
    # mtp-agp: (type-of x) gives x's type as a string, for debugging.
    def test_it_is_known_when_compiling(self):
        assert value("(real k 1 (>= 0)) (string s (type-of k))", "s") == "(real (>= 0))"
        assert value("(real|none c) (string s (type-of (+ c 1)))", "s") == "real|none"
