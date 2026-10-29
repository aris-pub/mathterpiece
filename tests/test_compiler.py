import math
from pathlib import Path

import pytest

from mathterpiece.compiler import CompileError, compile_scene
from mathterpiece.matrix import IDENTITY
from mathterpiece.nodes import Form, InterpStrLit, IntLit, Name, Pos, StrLit
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
            "(circle 'c' (r 3.5) (x -5.0) (y 4) (stroke 'teal') (stroke-width 1.5)"
            " (fill 'red') (opacity 0.25) (fill-opacity 0.5) (stroke-opacity 0.75))"
        )["c"]
        assert isinstance(c, Circle)
        assert (c.r, c.x, c.y) == (Free(3.5), Free(-5.0), Free(4.0))
        assert (c.stroke, c.fill, c.stroke_width) == (Free("teal"), Free("red"), Free(1.5))
        assert (c.opacity, c.fill_opacity, c.stroke_opacity) == (Free(0.25), Free(0.5), Free(0.75))

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
            ("fill", "false"),
            ("stroke", "2"),
            ("stroke-width", "'thick'"),
            ("opacity", "'half'"),
            ("r", "(+ 1 'a')"),
            ("r", "(+ 1 true)"),
        ],
    )
    def test_type_errors(self, attr, text):
        error(f"(circle 'c' ({attr} {text}))")

    def test_unknown_attribute(self):
        error("(circle 'c' (rr 2))", match="'rr' is not an attribute of circle")

    def test_hyphenated_attribute_read(self):
        scn = scene("(circle 'a' (stroke-width 2)) (circle 'c' (r a.stroke-width))")
        assert get(scn, "c", Circle).r == Bound(n("a", "stroke-width"))

    def test_underscore_field_name_is_not_an_attribute(self):
        error("(circle 'c' (stroke_width 2))", match="stroke_width")

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
        scn = scene("(circle 'teal_c' (stroke 'teal')) (circle 'c' (fill teal_c.stroke))")
        assert get(scn, "c", Circle).fill == Bound(n("teal_c", "stroke"))

    def test_string_attribute_where_real_expected(self):
        error("(circle 'teal_c') (circle 'c' (r teal_c.stroke))")

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

    def test_reference_moves_a_toplevel_object_into_the_group(self):
        scn = scene("(circle 'a') (circle 'b') (group 'g' a)")
        assert user_objects(scn) == [scn["b"], scn["g"]]

    def test_reference_moves_a_group_into_a_group(self):
        scn = scene("(group 'g' (circle 'a')) (group 'h' g)")
        assert user_objects(scn) == [scn["h"]]
        assert get(scn, "h", Group).members == [scn["g"]]

    @pytest.mark.parametrize(
        "src",
        [
            "(circle 'a') (group 'g' a) (group 'h' a)",
            "(group 'g' (circle 'a')) (group 'h' a)",
            "(group 'g' (circle 'a') a)",
            "(circle 'a') (group 'g' a a)",
            "(group 'g' (group 'h' (circle 'a'))) (group 'k' a)",
            "(circle 'a') (repeat i 2 (group $'g{i}' a))",
            "(group 'g' (circle 'a')) (group 'h' g[0])",
        ],
    )
    def test_an_object_has_one_parent(self, src):
        error(src, match="'a' already belongs to")

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
        scn = scene("(circle 'a') (canvas 'cnv' (view-x 0) (view-width 5) a (circle 'b'))")
        cnv = scn["cnv"]
        assert isinstance(cnv, Canvas)
        assert (cnv.view_x, cnv.view_width) == (Free(0.0), Free(5.0))
        assert (cnv.view_y, cnv.view_height) == (Free(-10.0), Free(20.0))
        assert cnv.members == [scn["a"], scn["b"]]

    def test_canvas_is_a_view(self):
        scn = scene("(canvas 'cnv')")
        assert scn.views == [scn["cnv"]]

    def test_attribute_after_members(self):
        error("(circle 'a') (canvas 'cnv' a (view-x 0))")

    def test_unknown_child(self):
        error(
            "(canvas 'cnv' (rr 2))",
            match="'rr' is not an attribute of canvas and not a recognized form",
        )

    def test_same_object_in_group_and_canvas(self):
        scn = scene("(circle 'a') (group 'g' a) (canvas 'cnv' a g)")
        assert get(scn, "cnv", Canvas).members == [scn["a"], scn["g"]]

    def test_showing_an_object_does_not_move_it(self):
        scn = scene("(circle 'a') (canvas 'cnv' a)")
        assert user_objects(scn) == [scn["a"]]

    def test_two_canvases_show_the_same_object(self):
        scn = scene("(circle 'a') (canvas 'c1' a) (canvas 'c2' a)")
        assert get(scn, "c2", Canvas).members == [scn["a"]]

    def test_objects_defined_in_a_canvas_are_toplevel(self):
        scn = scene("(canvas 'cnv' (circle 'a') (circle _))")
        cnv = get(scn, "cnv", Canvas)
        assert user_objects(scn) == cnv.members
        assert scn.views == [cnv]

    def test_object_defined_in_a_canvas_can_move_into_a_group(self):
        scn = scene("(canvas 'cnv' (circle 'a')) (group 'g' a)")
        assert user_objects(scn) == [scn["g"]]
        assert get(scn, "cnv", Canvas).members == [scn["a"]]

    @pytest.mark.parametrize("member", ["k", "other", "2"])
    def test_invalid_member(self, member):
        error(f"(real 'k') (canvas 'other') (canvas 'cnv' {member})")


def transform_of(src, name="cnv"):
    return get(scene(src), name, Canvas).transform


def applied(attr, x, y):
    assert isinstance(attr, Free)
    return pytest.approx(attr.value.apply(x, y))


class TestTransform:
    def test_default_is_identity(self):
        assert transform_of("(canvas 'cnv')") == Free(IDENTITY)

    def test_empty_is_identity(self):
        assert transform_of("(canvas 'cnv' (transform))") == Free(IDENTITY)

    def test_rotate_in_degrees_counterclockwise(self):
        attr = transform_of("(canvas 'cnv' (transform (rotate 90)))")
        assert isinstance(attr, Free)
        assert attr.value.apply(1, 0) == (0, 1)

    def test_rotate_takes_angle_conversions(self):
        attr = transform_of("(canvas 'cnv' (transform (rotate (turn 1/2))))")
        assert applied(attr, 1, 0) == (-1, 0)

    @pytest.mark.parametrize(
        "op, point", [("(scale 2)", (2, 2)), ("(scale 2 3)", (2, 3)), ("(scale -1 1)", (-1, 1))]
    )
    def test_scale(self, op, point):
        assert applied(transform_of(f"(canvas 'cnv' (transform {op}))"), 1, 1) == point

    def test_translate(self):
        assert applied(transform_of("(canvas 'cnv' (transform (translate 2 -1)))"), 1, 1) == (3, 0)

    def test_operations_run_left_to_right(self):
        rotate_first = transform_of("(canvas 'cnv' (transform (rotate 90) (translate 1 0)))")
        translate_first = transform_of("(canvas 'cnv' (transform (translate 1 0) (rotate 90)))")
        assert applied(rotate_first, 1, 0) == (1, 1)
        assert applied(translate_first, 1, 0) == (0, 2)

    def test_bound_keeps_the_whole_composition(self):
        attr = transform_of("(real 'k' 30) (canvas 'cnv' (transform (rotate k) (scale 2)))")
        expected = Form(
            (n("transform"), Form((n("rotate"), n("k"))), Form((n("scale"), IntLit(2))))
        )
        assert attr == Bound(expected)

    def test_another_transform_as_an_argument(self):
        src = (
            "(canvas 'a' (transform (rotate 10))) (canvas 'cnv' (transform a.transform (scale 2)))"
        )
        expected = Form((n("transform"), n("a", "transform"), Form((n("scale"), IntLit(2)))))
        assert transform_of(src) == Bound(expected)

    def test_loop_variable_is_free(self):
        attr = transform_of("(repeat i 2 (canvas $'c{i}' (transform (rotate (* 90 i)))))", "c1")
        assert applied(attr, 1, 0) == (0, 1)

    @pytest.mark.parametrize(
        "attr",
        [
            "(transform 30)",
            "(transform (rotate 'a'))",
            "(transform (rotate 1 2))",
            "(transform (rotate))",
            "(transform (scale))",
            "(transform (scale 1 2 3))",
            "(transform (translate 1))",
            "(transform k)",
            "(transform (rotate disk))",
        ],
    )
    def test_invalid(self, attr):
        error(f"(real 'k') (circle 'disk') (canvas 'cnv' {attr})")

    @pytest.mark.parametrize(
        "src",
        [
            "(circle 'c' (r (rotate 30)))",
            "(real 'v' (transform))",
            "(canvas 'cnv') (real 'v' cnv.transform)",
            "(real 'v' (+ 1 (scale 2)))",
        ],
    )
    def test_a_transform_is_not_a_number(self, src):
        error(src)

    def test_circles_have_no_transform(self):
        error("(circle 'c' (transform (rotate 30)))")


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
        assert (teal.name, teal.r, teal.fill) == ("teal_c", Free(3.5), Free("none"))
        assert (red.name, red.stroke, red.stroke_width) == ("red_c", Free("red"), Free(1.5))
        dots = [d for d in get(scn, "dots", Group).members if isinstance(d, Circle)]
        assert len(dots) == 150
        assert [d.name for d in dots] == [f"dot{i}" for i in range(150)]
        for d in dots:
            assert isinstance(d.fill, Bound)
            assert isinstance(d.fill.expr, Form)
            assert d.fill.expr.items[0] == n("cond")
        assert all(isinstance(d.r, Bound) and d.opacity == Free(0.25) for d in dots)
        assert get(scn, "cnv", Canvas).members == [scn["dots"], scn["circles"]]

    @pytest.mark.parametrize("example", sorted(EXAMPLES.glob("*.mtp")), ids=lambda p: p.name)
    def test_examples_compile(self, example):
        compile_scene(parse(example.read_text()))


class TestCycles:
    @pytest.mark.parametrize(
        "src, path",
        [
            ("(circle 'c' (x self.x))", "c.x -> c.x"),
            ("(circle 'c' (x self.y) (y self.x))", "c.x -> c.y -> c.x"),
            ("(circle 'c' (x self.y) (y self.r) (r self.x))", "c.x -> c.y -> c.r -> c.x"),
            ("(circle 'c' (x 1) (y self.r) (r (+ self.x self.y)))", "c.y -> c.r -> c.y"),
            ("(circle 'a') (circle 'c' (x (dist self a)))", "c.x -> c.x"),
            ("(circle 'a') (circle 'c' (y (dist a self)))", "c.y -> c.y"),
            ("(text 't' $'at {self.value}')", "t.value -> t.value"),
            ("(circle 'c' (fill (if (< self.r 1) self.fill 'red')))", "c.fill -> c.fill"),
            ("(canvas 'v' (view-x self.view-width) (view-width self.view-x))", "v.view-x"),
            ("(compound 'dot' (circle 'c')) (dot 'd' (x self.y) (y self.x))", "d.x -> d.y"),
            ("(compound 'dot' (circle 'c' (r self.r)))", "c.r -> c.r"),
            ("(group 'g' (circle _ (r self.r)))", "r -> r"),
        ],
    )
    def test_cycle_is_a_compile_error(self, src, path):
        error(src, match=f"circular.*{path}")

    def test_cycle_in_a_repeat(self):
        error("(repeat i 2 (circle $'c{i}' (x (+ i self.x))))", match="c0.x")

    def test_position_is_the_first_attribute_in_the_cycle(self):
        err = error("(circle 'c'\n  (r 1)\n  (x self.y)\n  (y self.x))")
        assert err.pos == Pos(3, 3)

    @pytest.mark.parametrize(
        "src",
        [
            "(circle 'c' (x 1) (y self.x) (r (+ self.x self.y)))",
            "(circle 'a') (circle 'c' (r (dist self a)))",
            "(circle 'c' (x 1) (y (dist 0 0 self.x 1)))",
            "(circle 'a' (x 1)) (circle 'c' (x a.y) (y a.x))",
            "(group 'g' (circle 'a' (r self.x)) (circle 'b' (x self.r)))",
        ],
    )
    def test_no_cycle(self, src):
        scene(src)


class TestSelf:
    def test_reads_own_attribute(self):
        c = get(scene("(circle 'c' (x 1) (y self.x))"), "c", Circle)
        assert c.y == Bound(n("self", "x"))

    def test_type_of_own_attribute_is_checked(self):
        error("(circle 'c' (r self.stroke))")

    def test_unknown_own_attribute(self):
        error("(circle 'c' (r self.nope))", match="nope")

    def test_self_in_interpolated_text(self):
        t = get(scene("(text 't' $'at {self.x}')"), "t", Text)
        assert t.value == Bound(InterpStrLit(("at ", n("self", "x"))))

    def test_rebound_by_nested_definition(self):
        scn = scene("(canvas 'cnv' (view-height self.view-width) (circle 'c' (r self.x)))")
        assert get(scn, "cnv", Canvas).view_height == Bound(n("self", "view-width"))
        assert get(scn, "c", Circle).r == Bound(n("self", "x"))

    def test_nested_self_is_not_the_container(self):
        error("(canvas 'cnv' (circle 'c' (r self.view-x)))", match="view-x")

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


class TestLoopVariablesInBoundExpressions:
    def test_replaced_by_their_value(self):
        scn = scene("(real 'k') (repeat i 2 (circle $'c{i}' (x (* i k))))")
        assert get(scn, "c1", Circle).x == Bound(Form((n("*"), IntLit(1), n("k"))))

    def test_replaced_inside_an_index(self):
        scn = scene("(group 'g' (circle 'a') (circle 'b')) (repeat i 2 (real $'k{i}' g[i].r))")
        assert get(scn, "k1", Real).value == Bound(n("g", IntLit(1), "r"))

    def test_replaced_inside_interpolated_text(self):
        scn = scene("(real 'k') (repeat i 2 (text $'t{i}' $'{i}: {k}'))")
        assert get(scn, "t1", Text).value == Bound(InterpStrLit(("1: ", n("k"))))

    def test_inner_variable_wins(self):
        scn = scene("(real 'k') (repeat i 1 (repeat i 3 (circle $'c{i}x' (x (* i k)))))")
        assert get(scn, "c2x", Circle).x == Bound(Form((n("*"), IntLit(2), n("k"))))


def bound_of(src):
    return get(scene(f"(real 'k' 2) (circle 'disk') (real 'v' {src})"), "v", Real).value


def real_of(src):
    return get(scene(f"(real 'v' {src})"), "v", Real).value


def text_of(src):
    return get(scene(f"(real 'k' 2) (text 't' {src})"), "t", Text).value


class TestComparisons:
    @pytest.mark.parametrize(
        "expr, result",
        [
            ("(< 1 2)", "a"),
            ("(< 2 1)", "b"),
            ("(<= 2 2)", "a"),
            ("(> 1/2 0.4)", "a"),
            ("(>= 1 2)", "b"),
            ("(= 1 1.0)", "a"),
            ("(= 'x' 'x')", "a"),
            ("(!= 'x' 'y')", "a"),
            ("(= true false)", "b"),
            ("(= 2i 2i)", "a"),
        ],
    )
    def test_folded(self, expr, result):
        assert text_of(f"(if {expr} 'a' 'b')") == Free(result)

    def test_bound(self):
        expr = Form((n("if"), Form((n("<"), n("k"), IntLit(3))), StrLit("a"), StrLit("b")))
        assert text_of("(if (< k 3) 'a' 'b')") == Bound(expr)

    @pytest.mark.parametrize(
        "expr",
        ["(< 1)", "(< 1 2 3)", "(< 1i 2i)", "(< 'a' 'b')", "(= 1 'a')", "(= true 1)", "(< disk 1)"],
    )
    def test_invalid(self, expr):
        error(f"(circle 'disk') (text 't' (if {expr} 'a' 'b'))")

    def test_result_is_bool_not_number(self):
        error("(real 'v' (< 1 2))")


class TestIf:
    def test_folds_when_condition_is_constant(self):
        assert real_of("(if true 1 2)") == Free(1.0)
        assert real_of("(if false 1 2)") == Free(2.0)

    def test_numeric_branches_widen(self):
        assert real_of("(if false 1 2.5)") == Free(2.5)

    def test_bound_when_condition_is_bound(self):
        assert isinstance(bound_of("(if (< k 1) 1 2)"), Bound)

    def test_bound_when_chosen_branch_is_bound(self):
        assert isinstance(bound_of("(if true k 2)"), Bound)

    @pytest.mark.parametrize(
        "expr",
        ["(if true 1)", "(if true 1 2 3)", "(if 1 2 3)", "(if 'yes' 2 3)", "(if true 1 'a')"],
    )
    def test_invalid(self, expr):
        error(f"(real 'v' {expr})")

    def test_unchosen_branch_is_still_checked(self):
        error("(real 'v' (if true 1 nope))", match="nope")


class TestCond:
    def test_first_true_clause(self):
        assert text_of("(cond (false 'a') (true 'b') (else 'c'))") == Free("b")

    def test_else(self):
        assert text_of("(cond (false 'a') (else 'c'))") == Free("c")

    def test_only_else(self):
        assert text_of("(cond (else 'c'))") == Free("c")

    def test_bound_condition(self):
        assert isinstance(text_of("(cond ((< k 1) 'a') (else 'c'))"), Bound)

    def test_constant_true_before_bound_condition_folds(self):
        assert text_of("(cond (true 'a') ((< k 1) 'b') (else 'c'))") == Free("a")

    def test_numeric_values_widen(self):
        assert real_of("(cond (false 1) (else 2.5))") == Free(2.5)

    @pytest.mark.parametrize(
        "expr",
        [
            "(cond)",
            "(cond (true 'a'))",
            "(cond (else 'a') (true 'b'))",
            "(cond (else 'a') (else 'b'))",
            "(cond (1 'a') (else 'b'))",
            "(cond (true 'a') (else 2))",
            "(cond (true) (else 'b'))",
            "(cond (true 'a' 'x') (else 'b'))",
            "(cond true (else 'b'))",
        ],
    )
    def test_invalid(self, expr):
        error(f"(text 't' {expr})")

    def test_else_outside_cond_is_undefined(self):
        error("(text 't' (if else 'a' 'b'))", match="else")


class TestPower:
    @pytest.mark.parametrize(
        "expr, value",
        [
            ("(^ 2 3)", 8.0),
            ("(^ 2 -1)", 0.5),
            ("(^ 1/2 2)", 0.25),
            ("(^ 4 0.5)", 2.0),
            ("(^ 2 0)", 1.0),
            ("(^ 0 0)", 1.0),
        ],
    )
    def test_folded(self, expr, value):
        assert real_of(expr) == Free(value)

    @pytest.mark.parametrize("expr", ["(^ 0 -1)", "(^ -8 1/3)", "(^ 2)", "(^ 2 3 4)", "(^ 'a' 2)"])
    def test_invalid(self, expr):
        error(f"(real 'v' {expr})")

    def test_bound(self):
        assert bound_of("(^ k 2)") == Bound(Form((n("^"), n("k"), IntLit(2))))


class TestSqrt:
    def test_folded(self):
        assert real_of("(sqrt 9)") == Free(3.0)

    def test_bound(self):
        assert isinstance(bound_of("(sqrt k)"), Bound)

    @pytest.mark.parametrize(
        "expr", ["(sqrt -1)", "(sqrt)", "(sqrt 1 2)", "(sqrt 'a')", "(sqrt 2i)"]
    )
    def test_invalid(self, expr):
        error(f"(real 'v' {expr})")


class TestAngles:
    @pytest.mark.parametrize(
        "expr, value",
        [
            (f"(rad {math.pi})", 180.0),
            ("(deg 45)", 45.0),
            ("(turn 1/4)", 90.0),
            ("(to-rad 180)", math.pi),
            ("(to-turn 90)", 0.25),
            ("(to-rad (rad 1))", 1.0),
        ],
    )
    def test_conversions(self, expr, value):
        assert real_of(expr) == Free(pytest.approx(value))

    @pytest.mark.parametrize(
        "expr, value",
        [
            (f"(sin {math.pi / 2})", 1.0),
            ("(cos 0)", 1.0),
            (f"(tan {math.pi / 4})", 1.0),
            ("(asin 1)", math.pi / 2),
            ("(acos 1)", 0.0),
            ("(atan 1)", math.pi / 4),
            ("(sind 30)", 0.5),
            ("(cosd 60)", 0.5),
            ("(tand 45)", 1.0),
            ("(asind 1)", 90.0),
            ("(acosd 0)", 90.0),
            ("(atand 1)", 45.0),
        ],
    )
    def test_trig(self, expr, value):
        assert real_of(expr) == Free(pytest.approx(value))

    @pytest.mark.parametrize(
        "expr, value",
        [("(sind 180)", 0.0), ("(cosd 90)", 0.0), ("(sind -90)", -1.0), ("(cosd 540)", -1.0)],
    )
    def test_degrees_are_exact_at_right_angles(self, expr, value):
        assert real_of(expr) == Free(value)

    def test_bound(self):
        assert bound_of("(sind k)") == Bound(Form((n("sind"), n("k"))))

    @pytest.mark.parametrize(
        "expr",
        ["(asin 2)", "(acosd -2)", "(tand 90)", "(tand -270)", "(sin)", "(sin 1 2)", "(rad 'a')"],
    )
    def test_invalid(self, expr):
        error(f"(real 'v' {expr})")


class TestDist:
    def test_two_objects(self):
        scn = scene("(circle 'a') (circle 'b') (real 'd' (dist a b))")
        assert get(scn, "d", Real).value == Bound(Form((n("dist"), n("a"), n("b"))))

    def test_with_self(self):
        scn = scene("(circle 'a') (circle 'b' (r (dist self a)))")
        assert isinstance(get(scn, "b", Circle).r, Bound)

    def test_with_indexed_member(self):
        scn = scene("(group 'g' (circle _) (circle _)) (real 'd' (dist g[0] g[1]))")
        assert isinstance(get(scn, "d", Real).value, Bound)

    def test_four_constant_numbers_fold(self):
        assert real_of("(dist 0 0 3 4)") == Free(5.0)

    def test_four_numbers_with_expressions(self):
        assert real_of("(dist 1/2 (* 2 1) 0.5 (- 2))") == Free(4.0)

    def test_four_numbers_bound(self):
        assert isinstance(bound_of("(dist k 0 0 disk.r)"), Bound)

    @pytest.mark.parametrize(
        "args",
        [
            "a",
            "a a a",
            "a 1",
            "1 2",
            "1 2 3",
            "1 2 3 4 5",
            "a k",
            "a g",
            "a cnv",
            "1 2 3 'x'",
            "1 2 3 2i",
            "1 2 3 a",
            "a b 1 2",
        ],
    )
    def test_invalid(self, args):
        error(
            "(circle 'a') (circle 'b') (real 'k') (group 'g') (canvas 'cnv')"
            f" (real 'd' (dist {args}))"
        )


class TestRef:
    def test_attribute_path(self):
        scn = scene("(circle 'a' (r 2)) (circle 'b' (r (ref 'a.r')))")
        assert get(scn, "b", Circle).r == Bound(n("a", "r"))

    def test_generated_name_in_repeat(self):
        scn = scene(
            "(repeat i 2 (circle $'c{i}')) (repeat i 2 (circle $'d{i}' (x (ref $'c{i}.x'))))"
        )
        assert get(scn, "d1", Circle).x == Bound(n("c1", "x"))

    def test_indexing_in_the_path(self):
        scn = scene(
            "(group 'g' (circle _ (r 3)) (circle _)) (repeat i 2 (real $'k{i}' (ref $'g[{i}].r')))"
        )
        assert get(scn, "k0", Real).value == Bound(n("g", IntLit(0), "r"))

    def test_param_gives_its_value(self):
        scn = scene("(real 'k' 2) (circle 'c' (r (ref 'k')))")
        assert get(scn, "c", Circle).r == Bound(n("k"))

    def test_builtin(self):
        assert get(scene("(real 'v' (ref 'pi'))"), "v", Real).value == Bound(n("pi"))

    def test_objects_for_dist(self):
        scn = scene("(circle 'a') (circle 'b') (real 'd' (dist (ref 'a') (ref 'b')))")
        assert get(scn, "d", Real).value == Bound(Form((n("dist"), n("a"), n("b"))))

    def test_member(self):
        scn = scene("(circle 'a') (canvas 'cnv' (ref 'a'))")
        assert get(scn, "cnv", Canvas).members == [scn["a"]]

    def test_members_from_repeat(self):
        scn = scene("(repeat i 2 (circle $'c{i}')) (canvas 'cnv' (repeat i 2 (ref $'c{i}')))")
        assert get(scn, "cnv", Canvas).members == [scn["c0"], scn["c1"]]

    def test_type_is_checked(self):
        error("(circle 'a' (stroke 'red')) (circle 'b' (r (ref 'a.stroke')))")

    @pytest.mark.parametrize(
        "arg",
        ["'nope'", "'a b'", "'1'", "''", "'a.'", "'+'", "k", "(rand)", "$'c{k}'", "'a' 'b'"],
    )
    def test_invalid(self, arg):
        error(f"(circle 'a') (real 'k') (circle 'c' (r (ref {arg})))")

    def test_no_argument(self):
        error("(circle 'c' (r (ref)))")

    def test_non_visual_member(self):
        error("(real 'k') (canvas 'cnv' (ref 'k'))")
