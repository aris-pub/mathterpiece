"""The compiler's core: declarations, names, the body rule and typed expressions (docs/syntax.md
sections 4, 8 and 9; docs/type-system.md sections 3 to 5.b)."""

import pytest
from helpers import error, model, value

from mathterpiece.compiler import compile_source
from mathterpiece.types import (
    BOOL,
    COLOR,
    INT,
    POINT,
    RATIO,
    REAL,
    STRING,
    ListT,
    Maybe,
    Refine,
)


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

    @pytest.mark.parametrize(
        "word", ["scene", "when", "else", "self", "const", "move", "transition"]
    )
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
        m = model("(scene s (circle_ (r 1)))")
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
        r = model("(scene s (real k 1 (>= 0)) (circle c (r (* 2 k))))").get("c").attrs["r"]
        assert r.expr.range[0] == 0

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
        r = model("(scene s (real k 1) (circle c (r (abs k))))").get("c").attrs["r"]
        assert r.expr.range[0] == 0


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


class TestFormatExponents:
    # A format's exponent has at least two digits, as Python writes a float's: 1.235e+04.
    def test_padded(self):
        assert value("(string s $'{12345.5:.3e}')", "s") == "1.235e+04"
        assert value("(string s $'{0.00001:g}')", "s") == "1e-05"


class TestAs:
    # (as T literal) gives a literal its type in place.
    def test_a_color_and_a_point(self):
        m = model(
            "(func shade (bool b) (if b (as color 'gold') (as color 'navy')))(color c (shade true))"
        )
        assert m.functions[m.funcs["shade"]].result == COLOR
        assert value("(point p (+ [1 1] (as point [0 0])))", "p") == (1, 1)

    def test_only_a_literal(self):
        error("(string s (as color 'blurple'))", "'blurple' is not a color")


class TestListRanges:
    # A list whose items all share a range carries it in its item type (type-system.md, "What
    # the compiler proves").
    def test_map_keeps_its_functions_range(self):
        src = (
            "(scene s (group g (circle a) (circle b)) (list rs (map g (fn p (dist [0 0] p.pos)))))"
        )
        t = model(src).get("rs").value.expr.type
        assert t.base.item == Refine(REAL, ((">=", 0),))

    def test_so_an_item_reaches_a_radius(self):
        m = model(
            "(scene s (group g (circle a) (circle b)) (list rs (map g (fn p (dist [0 0] p.pos))))"
            " (circle c (r (. rs 0))))"
        )
        assert m.get("c").attrs["r"].expr.type == Refine(REAL, ((">=", 0),))


class TestPowerRange:
    def test_power_takes_its_range_from_its_inputs(self):
        src = "(int h 0 (>= 0) (<= 3)) (real d (* 14 (^ 2 h)))"
        e = model(src).get("d").value.expr
        assert e.type == INT
        assert e.range == (14, 112)


class TestBoundListLength:
    # A list declared from an expression always equals it, so it keeps that expression's length;
    # a free list may be replaced by a move, so it needs (length n) (type-system.md, "Known
    # lengths").
    def test_a_bound_list_keeps_its_length(self):
        # So reading item 1 gives a real, never none.
        assert model("(real k 1) (list xs [k (* 2 k)]) (real d (. xs 1))").get("d").type == REAL

    def test_a_free_list_does_not(self):
        error("(list[real] xs [1 2]) (real d (. xs 1))", "may be none")


class TestMixedNumbers:
    def test_a_ratio_compared_with_a_real_is_compared_as_a_real(self):
        # As the runtime compares it: 2/5 is the real 0.4, which is not below 0.4.
        assert value("(bool b (< 2/5 0.4))", "b") is False

    def test_an_int_and_a_narrowed_real_meet_as_reals(self):
        xs = model("(real h 1 (>= 0)) (list xs [0 h])").get("xs").value
        assert xs.expr.type == ListT(Refine(REAL, ((">=", 0),)))


class TestListLiterals:
    # type-system.md section 3: a list written in brackets, even of expressions, is a literal,
    # and takes the type expected where it is written.
    def test_as_gives_a_type_to_a_list_of_expressions(self):
        # mtp-kk0
        m = model("(real k 1) (point q (as point [k 0]))")
        assert m.get("q").value.bound

    def test_a_branch_gives_its_type_to_a_list_literal_in_the_other(self):
        # mtp-vsx: inside a function nothing outside expects a type, so the other branch does.
        for src in (
            "(real k 1) (func f ((real a)) (if (> a 0) [a 0] (polar 1 30))) (point q (f k))",
            "(real k 1) (func f ((real a)) (if (> a 0) (polar 1 30) [a 0])) (point q (f k))",
        ):
            m = model(src)
            assert m.functions[m.funcs["f"]].result == POINT


class TestIndexingAListWrittenInPlace:
    # mtp-4vx: [a b c][h] reads item h of the list, as (. [a b c] h) does.
    def test_a_position_known_when_compiling(self):
        assert value("(real v [10 20 30][1])", "v") == 20

    def test_a_position_known_only_while_drawing(self):
        m = compile_source("(int h 0 (>= 0) (<= 2)) (real v [10 20 30][h])")
        assert m.get("v").value.bound


class TestBoundReadsKeepTheirRange:
    # mtp-2ixy: a bound variable always equals its expression, so a read of it has the
    # expression's range, not only its type's.
    def test_a_bound_variable_passed_to_a_constrained_parameter(self):
        m = model(
            "(real t 1 (>= 0.5) (<= 10.5)) (real L 2 (>= 2) (<= 10)) (real te (min t (+ L 0.5)))"
            " (func f ((real x (>= 0))) x) (real v (f te))"
        )
        assert m.get("te").value.expr.range == (0.5, 10.5)

    def test_a_bound_variable_as_a_radius(self):
        m = model("(point a) (point b) (real h (/ (dist a b) 2)) (scene s (circle c (r h)))")
        assert m.get("c").attrs["r"].expr.range[0] == 0

    def test_a_bound_variable_as_a_divisor(self):
        m = model("(real g 0 (>= 0) (<= 1)) (real lv (max 2 (* 10 g))) (real v (/ 1 lv))")
        assert m.get("v").value.expr.type == REAL

    def test_a_free_variable_keeps_its_type_range(self):
        # A writer may change it, so its starting value says nothing.
        error("(real k 2) (scene s (circle c (r k)))", "may break")


class TestLetInBodies:
    # mtp-b13: the standard let, in a foreach, group, scene or motif body: its body holds what
    # that body holds, and its names are values worked out where the let is written.
    def test_in_a_foreach(self):
        m = model(
            "(scene s (group g (foreach i 3 (let ((w (* 2 i)))"
            " (circle (name $'a{i}') (r w)) (circle (name $'b{i}') (r (+ w 1)))))))"
        )
        assert [m.get(f"a{i}").attrs["r"].value for i in range(3)] == [0, 2, 4]
        assert [m.get(f"b{i}").attrs["r"].value for i in range(3)] == [1, 3, 5]

    def test_a_value_known_only_while_drawing(self):
        m = model(
            "(real k 1 (>= 0))"
            " (scene s (foreach i 2 (let ((w (* k i))) (circle (name $'c{i}') (r w)))))"
        )
        # r reads the variable that holds w, which follows k (mtp-gvrf.2).
        ((held, _),) = m.get("c1").attrs["r"].deps
        assert m.objects[held].data["let"] == "w"
        assert m.objects[held].value.deps >= {(m.id("k"), None)}

    def test_in_a_group_and_the_scene(self):
        m = model("(scene s (let ((w 2)) (group g (let ((v (* w 3))) (circle c (r v))))))")
        assert m.get("c").attrs["r"].value == 6

    def test_in_a_motif(self):
        m = model(
            "(motif dot ((real t 1 (>= 0))) (let ((w (* 2 t))) (circle c (r w))))"
            " (scene s (dot d (t 3)))"
        )
        # A motif's parameter is an attribute of the instance, so r follows d.t, through the
        # variable that holds w.
        ((held, _),) = m.get("d.c").attrs["r"].deps
        assert m.objects[held].value.deps >= {(m.id("d"), "t")}

    def test_not_at_the_top_level(self):
        error("(let ((w 2)) (real k w))", "top level")

    def test_its_names_are_not_seen_after_it(self):
        error("(scene s (let ((w 2)) (circle a (r w))) (circle b (r w)))", "unknown name 'w'")


class TestForeach:
    # mtp-2mvr: (foreach i 5 decl…) counts from 0 to 4; (foreach p xs decl…) takes each item of
    # a list whose length is known when compiling, and (foreach m g decl…) each member of a group.
    def test_over_a_count(self):
        m = model("(scene s (foreach i 3 (circle (name $'c{i}') (r (+ i 1)))))")
        assert [m.get(f"c{i}").attrs["r"].value for i in range(3)] == [1, 2, 3]

    def test_over_a_list(self):
        m = model(
            "(list xs [4 5 6] (const)) (scene s (foreach x xs (circle (name $'c{x}') (r x))))"
        )
        assert m.get("c5").attrs["r"].value == 5

    def test_over_a_group(self):
        m = model(
            "(scene s (group g (circle a (r 1)) (circle b (r 2)))"
            " (foreach p g (circle (name $'ring-{p.name}') (r (* 2 p.r)))))"
        )
        assert m.get("ring-b").attrs["r"].deps >= {(m.id("b"), "r")}

    def test_over_a_spread(self):
        m = model(
            "(scene s (group g (circle a (x 1)) (circle b (x 2)))"
            " (foreach at g.pos (circle_ (pos at))))"
        )
        circles = [o for o in m.objects if o.kind == "circle"]
        assert len(circles) == 4 and circles[3].attrs["x"].deps >= {(m.id("b"), "x")}

    def test_a_writer_on_each_member(self):
        m = model(
            "(scene s (group g (circle a) (circle b))) (canvas v s (foreach p g (on-drag p p.pos)))"
        )
        drags = [o for o in m.objects if o.kind == "on-drag"]
        assert [o.data["target"][0] for o in drags] == [m.id("a"), m.id("b")]

    def test_the_count_or_length_must_be_known_when_compiling(self):
        assert model("(int n 2 (const)) (scene s (foreach i n (circle (name $'c{i}'))))").get("c1")
        error("(int n 2) (scene s (foreach i n (circle (name $'c{i}'))))", "known when compiling")

    def test_inside_a_group(self):
        m = model("(scene s (group g (foreach i 2 (circle (name $'m{i}')))))")
        assert [m.objects[j].name for j in m.get("g").members] == ["m0", "m1"]

    def test_a_plain_name_is_declared_twice(self):
        error("(scene s (foreach i 2 (circle c)))", "'c' is already declared")

    def test_several_declarations(self):
        m = model("(scene s (foreach i 2 (real (name $'k{i}') i) (circle (name $'c{i}'))))")
        assert m.get("k1").value.value == 1
        assert m.get("c1")

    def test_an_unexpected_item_is_shown_as_mtp(self):
        # mtp-1njz: the message printed the parser's internal form of the item.
        error(
            "(scene s (group g (foreach i 3 (real w (* 2 i)) (circle_ (r w)))))",
            r"^1:32: expected an argument such as \(r 1\), got \(real …\)$",
        )

    def test_repeat_is_gone(self):
        # mtp-091h: (repeat 2 i …) reads as a declaration of type repeat, which is not a type;
        # that is the error, rather than that 2 is not a name.
        error("(scene s (repeat 2 i (circle (name $'c{i}'))))", "1:11: unknown type 'repeat'")
        error("(blah 2 i)", "1:2: unknown type 'blah'")


class TestForeachOverSeveral:
    # mtp-h8f. The author, 2026-11-06: (foreach ((i n) (x xs) …) decl…), written as let writes
    # its names, beside (foreach i n …); every combination, the last changing fastest, as nested
    # foreach give; a source may read the names before it; a plain int n is (range n).
    def names(self, src):
        return [o.name for o in model(src).objects if o.kind == "circle"]

    def test_every_combination_the_last_fastest(self):
        src = "(scene s (foreach ((i 2) (j 3)) (circle (name $'c{i}{j}'))))"
        assert self.names(src) == ["c00", "c01", "c02", "c10", "c11", "c12"]

    def test_the_same_as_nested_foreach(self):
        body = "(circle (name $'c{i}-{x}') (r (+ i x)))"
        nested = model(f"(list xs [4 5] (const)) (scene s (foreach i 2 (foreach x xs {body})))")
        flat = model(f"(list xs [4 5] (const)) (scene s (foreach ((i 2) (x xs)) {body}))")
        assert [(o.name, o.attrs["r"].value) for o in flat.objects if o.kind == "circle"] == [
            (o.name, o.attrs["r"].value) for o in nested.objects if o.kind == "circle"
        ]

    def test_a_source_reads_the_names_before_it(self):
        src = "(scene s (foreach ((i 3) (j (range i))) (circle (name $'c{i}{j}'))))"
        assert self.names(src) == ["c10", "c20", "c21"]

    def test_over_a_group_and_a_count(self):
        src = (
            "(scene s (group g (circle a) (circle b))"
            " (foreach ((p g) (k 2)) (circle (name $'{p.name}{k}'))))"
        )
        assert self.names(src)[2:] == ["a0", "a1", "b0", "b1"]

    def test_inside_a_group_and_an_animation(self):
        m = model("(scene s (group g (foreach ((i 2) (j 2)) (circle (name $'m{i}{j}')))))")
        assert len(m.get("g").members) == 4
        m = model(
            "(real k 0) (animation a (in-order (foreach ((i 2) (j 2))"
            " (move k (to (+ i j)) (duration 1)))))"
        )
        assert len([o for o in m.objects if o.kind == "transition"]) == 4

    @pytest.mark.parametrize(
        "src, msg",
        [
            ("(scene s (foreach () (circle_)))", "at least one thing"),
            ("(scene s (foreach (i 2) (circle_)))", r"bindings as \(\(name source\) …\)"),
            ("(scene s (foreach ((i 2) (i 3)) (circle_)))", "foreach gives 'i' twice"),
            ("(scene s (foreach ((none 2)) (circle_)))", "expected the name foreach gives"),
            ("(int n 2) (scene s (foreach ((i 2) (j n)) (circle_)))", "known when compiling"),
        ],
    )
    def test_errors(self, src, msg):
        error(src, msg)


class TestTheFormTemplate:
    # syntax.md, section 8: a head, a name, positional arguments, optional arguments in any order,
    # then a body.
    K = "(real k 0 (>= 0) (<= 10))"

    @pytest.mark.parametrize(
        "src, arg, form",
        [
            ("(scene s (circle c) (background 'red'))", "background", "scene"),
            ("(scene s (group g (circle c) (fill 'red')))", "fill", "group"),
            ("(scene s (circle c)) (canvas v c (x 1))", "x", "canvas"),
            (
                f"{K} (button b (animation (move k (to 1) (duration 1))) (> k 1) (label 'go'))",
                "label",
                "button",
            ),
            (
                f"{K} (animation a (move k (to 1) (duration 1)) (defaults (duration 2)))",
                "defaults",
                "animation",
            ),
        ],
    )
    def test_an_optional_argument_comes_before_the_body(self, src, arg, form):
        error(src, rf"\({arg} …\) is an optional argument, so it comes before the {form}'s body")

    @pytest.mark.parametrize(
        "src",
        [
            "(scene s (background 'red') (circle c))",
            "(scene s (group g (translate [1 0]) (defaults (fill 'red') (stroke 'blue'))"
            " (circle c)))",
            "(scene s (circle c)) (canvas v (x 1) (toggle-duration 1) c)",
            f"{K} (button b (label 'go') (animation (move k (to 1) (duration 1))) (> k 1))",
            f"{K} (animation a (defaults (duration 2)) (move k (to 1)))",
        ],
    )
    def test_optional_arguments_in_any_order_then_the_body(self, src):
        # Only that each compiles: the other tests check what each argument does.
        model(src)


class TestForeachOverACountThatChanges:
    # The author, 2026-11-06: (foreach k n …) with n known only while drawing makes as many
    # copies as n can be at most, from its upper bound; copy k exists only while k < n.
    def test_as_many_copies_as_the_count_can_be(self):
        m = model("(int n 5 (>= 3) (<= 12)) (scene s (foreach k n (circle (name $'d{k}'))))")
        circles = [o for o in m.objects if o.kind == "circle"]
        assert len(circles) == 12
        assert all(isinstance(o.type, Maybe) and o.attrs["exists"].bound for o in circles)

    def test_a_count_needs_an_upper_bound(self):
        error("(int n 5 (>= 0)) (scene s (foreach k n (circle_)))", r"declare it with \(<= …\)")

    def test_an_exists_when_joins_the_copys_condition(self):
        m = model(
            "(int n 3 (>= 0) (<= 3)) (real cut 2)"
            " (scene s (foreach k n (circle (name $'c{k}'))"
            " (exists-when (name $'c{k}') (< k cut))))"
        )
        assert m.get("c1").attrs["exists"].expr.op == "and"

    def test_a_member_of_a_copy_goes_with_its_container(self):
        m = model(
            "(int n 1 (>= 0) (<= 2)) (scene s (foreach k n (group (name $'g{k}') (circle_))))"
        )
        (c, _) = [o for o in m.objects if o.kind == "circle"]
        assert "exists" not in c.attrs and isinstance(c.type, Maybe)

    def test_a_known_count_is_as_before(self):
        m = model("(scene s (foreach k 3 (circle (name $'d{k}'))))")
        assert not any("exists" in o.attrs for o in m.objects if o.kind == "circle")


class TestIfWithAKnownCondition:
    # The author, 2026-11-06: an if whose condition is known when compiling compiles only the
    # branch it takes, so a foreach copy can start a chain: (if (= k 0) start (… previous …)).
    def test_each_copy_from_the_one_before(self):
        m = model(
            "(scene s (foreach k 3 (circle (name $'d{k}')"
            " (x (if (= k 0) 1 (* 2 (. (name $'d{(- k 1)}') x)))))))"
        )
        assert [m.get(f"d{k}").attrs["x"].value for k in range(3)] == [1, 2, 4]

    def test_the_branch_taken_meets_what_the_if_is_given_to(self):
        assert (
            model("(scene s (circle c (pos (if true [1 0] none))))").get("c").attrs["x"].value == 1
        )
