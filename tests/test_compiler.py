import math
from pathlib import Path

import pytest

from mathterpiece.compiler import CompileError, compile_scene
from mathterpiece.nodes import Form, InterpStrLit, IntLit, Name, Pos
from mathterpiece.parse import parse
from mathterpiece.scene import Bound, Canvas, Circle, Free, Group, Real, Text

EXAMPLES = Path(__file__).parent.parent / "examples"


def scene(src):
    return compile_scene(parse(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match) as exc:
        scene(src)
    return exc.value


def n(*parts):
    return Name(tuple(parts))


def get[T](scn, name, cls: type[T]) -> T:
    obj = scn[name]
    assert isinstance(obj, cls)
    return obj


BUILTINS = {"pi", "π", "tau", "τ", "euler", "infty", "∞"}


def user_objects(scn):
    return [obj for obj in scn.objects if obj.name not in BUILTINS]


class TestBuiltins:
    @pytest.mark.parametrize(
        "name, value",
        [("pi", math.pi), ("tau", math.tau), ("euler", math.e), ("infty", math.inf)],
    )
    def test_builtin_is_a_real(self, name, value):
        obj = scene("")[name]
        assert isinstance(obj, Real)
        assert obj.value == Free(value)

    @pytest.mark.parametrize("alias, name", [("π", "pi"), ("τ", "tau"), ("∞", "infty")])
    def test_alias_is_the_same_object(self, alias, name):
        scn = scene("")
        assert scn[alias] is scn[name]

    def test_inf_is_not_defined(self):
        assert "inf" not in scene("")

    def test_builtins_come_first_in_order(self):
        scn = scene("(circle 'a')")
        assert [obj.name for obj in scn.objects] == ["pi", "tau", "euler", "infty", "a"]

    def test_user_definition_replaces_builtin(self):
        scn = scene("(real 'pi' 3)")
        assert get(scn, "pi", Real).value == Free(3.0)

    def test_replaced_builtin_keeps_its_other_name(self):
        scn = scene("(real 'pi' 3)")
        builtin = get(scn, "π", Real)
        assert builtin is not scn["pi"]
        assert builtin.name == "π"
        assert builtin.value == Free(math.pi)

    def test_use_before_replacing_definition_is_error(self):
        error("(circle 'c' (r pi)) (real 'pi' 3)", match="pi")

    def test_bare_builtin_name_is_bound(self):
        assert get(scene("(circle 'c' (r pi))"), "c", Circle).r == Bound(n("pi"))


class TestCircle:
    def test_defaults(self):
        c = scene("(circle 'c')")["c"]
        assert c == Circle(name="c")

    def test_given_attributes(self):
        c = scene(
            "(circle 'c' (r 3.5) (x -5.0) (y 4) (edgecolor 'teal') (linewidth 1.5)"
            " (fill false) (alpha 0.25) (facecolor 'red'))"
        )["c"]
        assert isinstance(c, Circle)
        assert (c.r, c.x, c.y) == (Free(3.5), Free(-5.0), Free(4.0))
        assert (c.edgecolor, c.facecolor) == (Free("teal"), Free("red"))
        assert (c.linewidth, c.fill, c.alpha) == (Free(1.5), Free(False), Free(0.25))

    @pytest.mark.parametrize("text", ["2", "1/2", "2.0", "(* 2 3)", "(/ 1 2)"])
    def test_numbers_are_widened_to_real(self, text):
        r = get(scene(f"(circle 'c' (r {text}))"), "c", Circle).r
        assert isinstance(r, Free)
        assert type(r.value) is float

    @pytest.mark.parametrize(
        "text, value",
        [
            ("(+ 1 2)", 3.0),
            ("(- 5 2)", 3.0),
            ("(* 2 3)", 6.0),
            ("(/ 1 2)", 0.5),
            ("(/ 4 2)", 2.0),
            ("(- 2)", -2.0),
            ("(+ 1 (* 2 3))", 7.0),
            ("(+ 1/2 1/2)", 1.0),
            ("(+)", 0.0),
            ("(*)", 1.0),
            ("(* 2 0.5)", 1.0),
        ],
    )
    def test_constant_expressions_are_folded(self, text, value):
        assert get(scene(f"(circle 'c' (r {text}))"), "c", Circle).r == Free(value)

    @pytest.mark.parametrize(
        "attr, text",
        [
            ("r", "'big'"),
            ("r", "true"),
            ("r", "2i"),
            ("r", "$'x'"),
            ("fill", "1"),
            ("fill", "'yes'"),
            ("edgecolor", "2"),
            ("edgecolor", "false"),
            ("r", "(+ 1 'a')"),
            ("r", "(+ 1 true)"),
        ],
    )
    def test_type_errors(self, attr, text):
        error(f"(circle 'c' ({attr} {text}))")

    def test_unknown_attribute(self):
        error("(circle 'c' (rr 2))", match="'rr' is not an attribute of circle")

    def test_attribute_given_twice(self):
        error("(circle 'c' (r 1) (r 2))", match="'r'")

    @pytest.mark.parametrize("text", ["(r)", "(r 1 2)"])
    def test_attribute_takes_one_value(self, text):
        error(f"(circle 'c' {text})")

    def test_attribute_name_must_be_a_name(self):
        error("(circle 'c' ('r' 2))")

    def test_no_positional_values(self):
        error("(circle 'c' 2)")

    @pytest.mark.parametrize(
        "src", ["(-)", "(/)", "(/ 2)", "(/ 1 0)", "(/ 1/2 0)", "(/ 1.0 0)", "(/ 1 0.0)"]
    )
    def test_invalid_constant_arithmetic(self, src):
        error(f"(circle 'c' (r {src}))")


class TestNames:
    def test_name_is_required(self):
        error("(circle)")

    @pytest.mark.parametrize("name", ["c", "2", "true", "(f)"])
    def test_name_must_be_a_string_or_underscore(self, name):
        error(f"(circle {name})")

    def test_duplicate_name(self):
        err = error("(circle 'a')\n(real 'a')", match="'a'")
        assert err.pos == Pos(2, 1)

    def test_underscore_makes_an_anonymous_object(self):
        scn = scene("(group 'g' (circle _ (r 2)))")
        g = scn["g"]
        assert isinstance(g, Group)
        (c,) = g.members
        assert isinstance(c, Circle)
        assert c.name is None
        assert c.r == Free(2.0)

    def test_anonymous_toplevel_object(self):
        scn = scene("(circle _) (circle _)")
        assert len(user_objects(scn)) == 2

    def test_interpolated_name_with_bound_value_is_error(self):
        error("(real 'k') (circle $'c{k}')")

    def test_undefined_name(self):
        error("(circle 'c' (r nope))", match="nope")

    def test_use_before_definition_is_error(self):
        error("(circle 'c' (r k)) (real 'k')", match="k")

    def test_unknown_attribute_of_object(self):
        error("(circle 'disk') (circle 'c' (r disk.nope))", match="nope")

    def test_attribute_of_a_real_is_error(self):
        error("(real 'k') (circle 'c' (r k.value.x))")


class TestReal:
    def test_default(self):
        assert scene("(real 'k')")["k"] == Real(name="k", value=Free(0.0))

    @pytest.mark.parametrize("text, value", [("2", 2.0), ("1/2", 0.5), ("-0.1", -0.1)])
    def test_value_by_position(self, text, value):
        k = get(scene(f"(real 'k' {text})"), "k", Real)
        assert k.value == Free(value)
        assert isinstance(k.value, Free)
        assert type(k.value.value) is float

    def test_bound_value(self):
        expr = Form((n("*"), IntLit(2), n("disk", "r")))
        k = get(scene("(circle 'disk') (real 'k' (* 2 disk.r))"), "k", Real)
        assert k.value == Bound(expr)

    def test_value_cannot_be_given_as_attribute(self):
        error("(real 'k' (value 2))")

    def test_value_given_twice(self):
        error("(real 'k' 2 3)")

    @pytest.mark.parametrize("text", ["'x'", "true", "2i"])
    def test_type_errors(self, text):
        error(f"(real 'k' {text})")


class TestText:
    def test_default(self):
        assert get(scene("(text 'lbl')"), "lbl", Text).value == Free("")

    def test_value_by_position(self):
        t = scene("(text 'lbl' 'hello' (x 1))")["lbl"]
        assert isinstance(t, Text)
        assert (t.value, t.x) == (Free("hello"), Free(1.0))

    def test_constant_interpolated_string_is_folded(self):
        assert get(scene("(text 'lbl' $'plain')"), "lbl", Text).value == Free("plain")

    def test_interpolated_string_with_scene_object_is_bound(self):
        t = scene("(circle 'disk') (text 'lbl' $'r = {disk.r}')")["lbl"]
        assert t.value == Bound(InterpStrLit(("r = ", n("disk", "r"))))

    @pytest.mark.parametrize("text", ["pi", "2", "true", "(+ 1 2)"])
    def test_numbers_are_not_text(self, text):
        error(f"(text 'lbl' {text})")

    def test_value_cannot_be_given_as_attribute(self):
        error("(text 'lbl' (value 'x'))")

    def test_too_many_positional_values(self):
        error("(text 'lbl' 'a' 'b')")


class TestBound:
    @pytest.mark.parametrize(
        "text, expr",
        [
            ("k", n("k")),
            ("disk.r", n("disk", "r")),
            ("(* 2 disk.r)", Form((n("*"), IntLit(2), n("disk", "r")))),
            ("(+ k 1)", Form((n("+"), n("k"), IntLit(1)))),
            ("(- k)", Form((n("-"), n("k")))),
            ("(rand)", Form((n("rand"),))),
            ("(rand 0 1)", Form((n("rand"), IntLit(0), IntLit(1)))),
            ("(* 2 (rand))", Form((n("*"), IntLit(2), Form((n("rand"),))))),
        ],
    )
    def test_expression_is_stored_as_written(self, text, expr):
        scn = scene(f"(real 'k') (circle 'disk') (circle 'c' (r {text}))")
        assert get(scn, "c", Circle).r == Bound(expr)

    def test_string_attribute_from_another_object(self):
        scn = scene(
            "(circle 'teal_c' (edgecolor 'teal')) (circle 'c' (facecolor teal_c.edgecolor))"
        )
        assert get(scn, "c", Circle).facecolor == Bound(n("teal_c", "edgecolor"))

    def test_string_attribute_where_real_expected(self):
        error("(circle 'teal_c') (circle 'c' (r teal_c.edgecolor))")

    def test_object_where_value_expected(self):
        error("(circle 'disk') (circle 'c' (r disk))")

    def test_object_in_arithmetic(self):
        error("(circle 'disk') (circle 'c' (r (+ disk 1)))")


class TestRand:
    @pytest.mark.parametrize("text", ["(rand 1)", "(rand 0 1 2)", "(rand 0 'a')", "(rand true 1)"])
    def test_invalid(self, text):
        error(f"(circle 'c' (r {text}))")

    def test_rand_is_real_so_not_text(self):
        error("(text 'lbl' (rand))")


class TestGroup:
    def test_empty(self):
        assert scene("(group 'g')")["g"] == Group(name="g")

    def test_inline_members(self):
        scn = scene("(group 'g' (circle 'a') (text 'b'))")
        g = scn["g"]
        assert isinstance(g, Group)
        assert g.members == [scn["a"], scn["b"]]
        assert user_objects(scn) == [g]

    def test_members_by_reference(self):
        scn = scene("(circle 'a') (group 'g' a)")
        assert get(scn, "g", Group).members == [scn["a"]]

    def test_nested_group(self):
        scn = scene("(group 'g' (group 'h' (circle 'a')))")
        assert get(scn, "h", Group).members == [scn["a"]]

    def test_group_takes_no_attributes(self):
        error(
            "(group 'g' (r 2))", match="'r' is not an attribute of group and not a recognized form"
        )

    @pytest.mark.parametrize("member", ["2", "'a'", "true", "k", "cnv"])
    def test_invalid_member(self, member):
        error(f"(real 'k') (canvas 'cnv') (group 'g' {member})")

    def test_canvas_cannot_be_defined_in_a_group(self):
        error("(group 'g' (canvas 'cnv'))")

    def test_real_cannot_be_defined_in_a_group(self):
        error("(group 'g' (real 'k'))")


class TestGroupAttributes:
    def test_spliced_into_arithmetic(self):
        scn = scene("(group 'g' (circle 'a') (circle 'b')) (real 's' (+ g.r))")
        assert get(scn, "s", Real).value == Bound(Form((n("+"), n("g", "r"))))

    def test_spliced_into_interpolated_string(self):
        scn = scene("(group 'g' (circle 'a')) (text 't' $'radii: {g.r}')")
        assert get(scn, "t", Text).value == Bound(InterpStrLit(("radii: ", n("g", "r"))))

    def test_where_one_value_expected(self):
        error("(group 'g' (circle 'a') (circle 'b')) (circle 'c' (r g.r))")

    def test_member_without_the_attribute(self):
        error("(group 'g' (circle 'a') (text 't')) (real 's' (+ g.r))", match="'r'")

    def test_indexing_a_member(self):
        scn = scene("(group 'g' (circle _ (r 2))) (real 'k' g[0].r)")
        assert get(scn, "k", Real).value == Bound(n("g", IntLit(0), "r"))

    def test_negative_index(self):
        scn = scene("(group 'g' (circle 'a') (circle 'b')) (real 'k' g[-1].r)")
        assert get(scn, "k", Real).value == Bound(n("g", IntLit(-1), "r"))

    @pytest.mark.parametrize("index", ["2", "-3"])
    def test_index_out_of_range(self, index):
        error(f"(group 'g' (circle 'a') (circle 'b')) (real 'k' g[{index}].r)")

    def test_index_must_be_an_int(self):
        error("(group 'g' (circle 'a')) (real 'k' g[0.5].r)")


class TestCanvas:
    def test_defaults(self):
        assert scene("(canvas 'cnv')")["cnv"] == Canvas(name="cnv")

    def test_attributes_then_members(self):
        scn = scene("(circle 'a') (canvas 'cnv' (xmin 0) (xmax 5) a (circle 'b'))")
        cnv = scn["cnv"]
        assert isinstance(cnv, Canvas)
        assert (cnv.xmin, cnv.xmax) == (Free(0.0), Free(5.0))
        assert cnv.members == [scn["a"], scn["b"]]

    def test_canvas_is_a_view(self):
        scn = scene("(canvas 'cnv')")
        assert scn.views == [scn["cnv"]]

    def test_attribute_after_members(self):
        error("(circle 'a') (canvas 'cnv' a (xmin 0))")

    def test_unknown_child(self):
        error(
            "(canvas 'cnv' (rr 2))",
            match="'rr' is not an attribute of canvas and not a recognized form",
        )

    def test_same_object_in_group_and_canvas(self):
        scn = scene("(circle 'a') (group 'g' a) (canvas 'cnv' a g)")
        assert get(scn, "cnv", Canvas).members == [scn["a"], scn["g"]]

    @pytest.mark.parametrize("member", ["k", "other", "2"])
    def test_invalid_member(self, member):
        error(f"(real 'k') (canvas 'other') (canvas 'cnv' {member})")


class TestToplevel:
    @pytest.mark.parametrize("src", ["(+ 1 2)", "(r 2)", "(rand)"])
    def test_not_a_definition(self, src):
        error(src)

    def test_unknown_form(self):
        error("(square 'sq')", match="square")

    def test_error_has_position(self):
        err = error("(circle 'a')\n  (circle 'b' (r 'x'))")
        assert err.pos.line == 2
        assert str(err).startswith("2:")


class TestRepeat:
    def test_toplevel_repeat_splices(self):
        scn = scene("(repeat i 3 (circle $'c{i}' (x i)))")
        assert [obj.name for obj in user_objects(scn)] == ["c0", "c1", "c2"]
        assert [get(scn, f"c{i}", Circle).x for i in range(3)] == [Free(0.0), Free(1.0), Free(2.0)]

    def test_repeat_in_group(self):
        scn = scene("(group 'g' (repeat i 2 (circle $'c{i}')))")
        assert [m.name for m in get(scn, "g", Group).members] == ["c0", "c1"]

    def test_repeat_in_canvas(self):
        scn = scene("(canvas 'cnv' (repeat i 2 (circle $'c{i}')))")
        assert [m.name for m in get(scn, "cnv", Canvas).members] == ["c0", "c1"]

    def test_repeat_next_to_other_members(self):
        scn = scene("(group 'g' (circle 'a') (repeat i 2 (circle $'c{i}')) (circle 'b'))")
        assert [m.name for m in get(scn, "g", Group).members] == ["a", "c0", "c1", "b"]

    def test_several_body_forms_by_iteration(self):
        scn = scene("(repeat i 2 (circle $'c{i}') (text $'t{i}' 'x'))")
        assert [obj.name for obj in user_objects(scn)] == ["c0", "t0", "c1", "t1"]

    def test_zero_times(self):
        assert user_objects(scene("(repeat i 0 (circle $'c{i}'))")) == []

    def test_count_from_constant_expression(self):
        assert len(user_objects(scene("(repeat i (+ 1 2) (circle $'c{i}'))"))) == 3

    def test_loop_variable_in_constant_expression(self):
        scn = scene("(repeat i 2 (circle $'c{i}' (x (* i 2))))")
        assert get(scn, "c1", Circle).x == Free(2.0)

    def test_count_from_outer_loop_variable(self):
        scn = scene("(repeat i 3 (repeat j i (circle $'c{i}{j}')))")
        assert [obj.name for obj in user_objects(scn)] == ["c10", "c20", "c21"]

    def test_nested_repeat(self):
        scn = scene("(repeat i 2 (repeat j 2 (circle $'c{i}{j}' (x j) (y i))))")
        assert [obj.name for obj in user_objects(scn)] == ["c00", "c01", "c10", "c11"]
        c10 = get(scn, "c10", Circle)
        assert (c10.x, c10.y) == (Free(0.0), Free(1.0))

    def test_inner_loop_variable_shadows_and_restores_outer(self):
        scn = scene(
            "(repeat i 2 (group $'g{i}' (repeat i 3 (circle _ (x i)))) (circle $'b{i}' (x i)))"
        )
        assert [get(scn, f"b{i}", Circle).x for i in range(2)] == [Free(0.0), Free(1.0)]
        members = get(scn, "g1", Group).members
        assert [m.x for m in members if isinstance(m, Circle)] == [Free(0.0), Free(1.0), Free(2.0)]

    def test_loop_variable_is_not_in_the_scene(self):
        error("(repeat i 2 (circle $'c{i}')) (real 'k' i)", match="i")

    def test_same_name_each_iteration_is_duplicate(self):
        error("(repeat i 2 (circle 'a'))", match="'a'")

    def test_loop_variable_must_be_a_name(self):
        error("(repeat 'i' 2 (circle $'c{i}'))")

    @pytest.mark.parametrize("count", ["2.5", "-1", "1/2", "'x'", "true", "k", "(rand)"])
    def test_invalid_count(self, count):
        error(f"(real 'k') (repeat i {count} (circle _))")

    def test_missing_count(self):
        error("(repeat i)")


class TestExamples:
    def test_dots(self):
        scn = compile_scene(parse((EXAMPLES / "dots.mtp").read_text()))
        teal, red = get(scn, "circles", Group).members
        assert isinstance(teal, Circle) and isinstance(red, Circle)
        assert (teal.name, teal.r, teal.fill) == ("teal_c", Free(3.5), Free(False))
        assert (red.name, red.edgecolor) == ("red_c", Free("red"))
        dots = [d for d in get(scn, "dots", Group).members if isinstance(d, Circle)]
        assert len(dots) == 100
        assert [d.name for d in dots] == [f"dot{i}" for i in range(100)]
        assert all(d.facecolor == Bound(n("teal_c", "edgecolor")) for d in dots)
        assert all(isinstance(d.r, Bound) and d.alpha == Free(0.25) for d in dots)
        assert get(scn, "cnv", Canvas).members == [scn["dots"], scn["circles"]]

    @pytest.mark.parametrize("example", sorted(EXAMPLES.glob("*.mtp")), ids=lambda p: p.name)
    def test_examples_compile(self, example):
        compile_scene(parse(example.read_text()))


class TestSelf:
    def test_reads_own_attribute(self):
        c = get(scene("(circle 'c' (x 1) (y self.x))"), "c", Circle)
        assert c.y == Bound(n("self", "x"))

    def test_type_of_own_attribute_is_checked(self):
        error("(circle 'c' (r self.edgecolor))")

    def test_unknown_own_attribute(self):
        error("(circle 'c' (r self.nope))", match="nope")

    def test_self_in_interpolated_text(self):
        t = get(scene("(text 't' $'at {self.x}')"), "t", Text)
        assert t.value == Bound(InterpStrLit(("at ", n("self", "x"))))

    def test_rebound_by_nested_definition(self):
        scn = scene("(canvas 'cnv' (xmax self.xmin) (circle 'c' (r self.x)))")
        assert get(scn, "cnv", Canvas).xmax == Bound(n("self", "xmin"))
        assert get(scn, "c", Circle).r == Bound(n("self", "x"))

    def test_nested_self_is_not_the_container(self):
        error("(canvas 'cnv' (circle 'c' (r self.xmin)))", match="xmin")

    def test_shadows_a_global_named_self(self):
        c = get(scene("(real 'self' 2) (circle 'c' (r self.x))"), "c", Circle)
        assert c.r == Bound(n("self", "x"))

    def test_bare_self_is_an_object(self):
        error("(circle 'c' (r self))")

    def test_not_allowed_in_a_name(self):
        error("(circle $'c{self.x}')")

    def test_not_a_member(self):
        error("(group 'g' self)")

    def test_undefined_outside_definitions(self):
        error("(repeat i self.x (circle _))", match="self")
