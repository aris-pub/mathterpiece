import random

import pytest
from helpers import user_objects, with_scene
from matplotlib.colors import to_rgba

from mathterpiece.backends.mpl import Evaluator, render
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.model import (
    Bound,
    Circle,
    Free,
    Group,
    Inherit,
    Model,
    Motif,
    Styled,
    attributes,
    local_names,
)
from mathterpiece.nodes import Name

DOT = "(motif 'dot' (params (r 1.0)) (circle 'c' (r r)))"
BUILTINS = {"pi", "π", "tau", "τ", "euler", "infty", "∞"}


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def n(*parts):
    return Name(tuple(parts))


def get[T](scn, name, cls: type[T]) -> T:
    obj = scn[name]
    assert isinstance(obj, cls)
    return obj


def member[T](motif, name, cls: type[T]) -> T:
    obj = local_names(motif)[name]
    assert isinstance(obj, cls)
    return obj


class TestSceneModel:
    def test_attributes_are_the_styled_ones_and_members(self):
        assert list(attributes(Motif)) == [*attributes(Styled), "members"]

    def test_member_names_are_not_global(self):
        a = Motif(name="a", kind="dot", members=[Circle(name="c")])
        b = Motif(name="b", kind="dot", members=[Circle(name="c")])
        scn = Model()
        scn.add(a)
        scn.add(b)
        assert "a" in scn
        assert "c" not in scn

    def test_local_names_go_through_groups_but_not_motifs(self):
        inner = Motif(name="i", kind="k", members=[Circle(name="deep")])
        g = Group(name="g", members=[Circle(name="a"), inner])
        outer = Motif(name="o", kind="k", members=[g, Circle(name="b")])
        assert set(local_names(outer)) == {"g", "a", "i", "b"}

    def test_one_parent_inside_motifs(self):
        c = Circle(name="c")
        scn = Model()
        scn.add(Motif(name="a", kind="dot", members=[c]))
        with pytest.raises(ValueError):
            scn.add(Group(name="g", members=[c]))


class TestDefinition:
    def test_definition_is_not_drawn(self):
        assert user_objects(scene(DOT)) == []

    def test_params_are_optional(self):
        d = get(scene("(motif 'dot' (circle 'c')) (dot 'd')"), "d", Motif)
        assert d.params == {}

    def test_body_is_checked_without_an_instance(self):
        error("(motif 'dot' (circle 'c' (r nope)))", match="nope")

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(motif 'dot' (params (x 1)) (circle 'c'))", "x"),
            ("(motif 'dot' (params (fill 'red')) (circle 'c'))", "fill"),
            ("(motif 'dot' (params (r 1) (r 2)) (circle 'c'))", "r"),
            ("(motif 'dot' (params (c 1)) (circle 'c'))", "c"),
            ("(real 'k') (motif 'dot' (params (r k)) (circle 'c'))", "compile time"),
            ("(motif 'dot' (params (r)) (circle 'c'))", None),
            ("(motif 'dot' (params r) (circle 'c'))", None),
            ("(motif 'dot' (circle 'c') (params (r 1)))", "params"),
            ("(motif 'dot' (params (r 1)) (params (s 1)))", "params"),
            ("(motif 'dot' (circle 'c')) (motif 'dot' (circle 'c'))", "dot"),
            ("(motif dot (circle 'c'))", None),
            ("(motif 'dot' (circle 'c') (circle 'c'))", "'c'"),
            ("(circle 'a') (motif 'dot' a)", "body"),
            ("(motif 'dot' (canvas 'cnv'))", None),
            ("(motif 'dot' (real 'k'))", None),
            ("(group 'g' (motif 'dot' (circle 'c')))", None),
            ("(motif 'dot' (motif 'inner' (circle 'c')))", None),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


SYNTAX = ["motif", "params", "repeat", "ref", "if", "cond", "else", "transform"]


class TestLibraryForms:
    def test_motif_hides_a_library_form(self):
        c = get(scene("(motif 'circle' (text 't' 'hi')) (circle 'c')"), "c", Motif)
        assert c.kind == "circle"

    def test_a_motif_after_the_scene_does_not_change_it(self):
        scn = scene("(scene _ (circle 'a')) (motif 'circle' (text 't' 'hi'))")
        assert isinstance(scn["a"], Circle)

    def test_body_of_the_motif_uses_the_library_form(self):
        d = get(scene("(motif 'circle' (circle 'c' (r 2))) (circle 'd')"), "d", Motif)
        assert member(d, "c", Circle).r == Free(2.0)

    @pytest.mark.parametrize("name", SYNTAX)
    def test_syntax_names_are_not_motif_names(self, name):
        error(f"(motif '{name}' (circle 'c'))", match=name)

    @pytest.mark.parametrize("name", SYNTAX)
    def test_syntax_names_are_not_object_names(self, name):
        error(f"(circle '{name}')", match=name)

    @pytest.mark.parametrize("name", SYNTAX)
    def test_syntax_names_are_not_interpolated_object_names(self, name):
        error(f"(circle $'{name}')", match=name)

    @pytest.mark.parametrize("name", SYNTAX)
    def test_syntax_names_are_not_parameter_names(self, name):
        error(f"(motif 'dot' (params ({name} 1)) (circle 'c'))", match=name)

    @pytest.mark.parametrize("name", SYNTAX)
    def test_syntax_names_are_not_loop_variables(self, name):
        error(f"(repeat 2 {name} (circle _))", match=name)


class TestInstance:
    def test_default_params(self):
        d = get(scene(f"{DOT} (dot 'd')"), "d", Motif)
        assert d.kind == "dot"
        assert d.params == {"r": Free(1.0)}
        assert member(d, "c", Circle).r == Free(1.0)

    def test_given_params(self):
        d = get(scene(f"{DOT} (dot 'd' (r 2))"), "d", Motif)
        assert d.params == {"r": Free(2.0)}
        assert member(d, "c", Circle).r == Free(2.0)

    def test_bound_params(self):
        d = get(scene(f"(real 'k' 2) {DOT} (dot 'd' (r k))"), "d", Motif)
        assert d.params == {"r": Bound(n("k"))}
        assert member(d, "c", Circle).r == Bound(n("r"))

    def test_param_type_is_the_default_type(self):
        error("(motif 'dot' (params (n 1)) (circle 'c')) (dot 'd' (n 2.5))")
        error("(motif 'dot' (params (s 'a')) (circle 'c')) (dot 'd' (s 1))")

    def test_param_types_widen(self):
        d = get(scene(f"{DOT} (dot 'd' (r 1/2))"), "d", Motif)
        assert d.params == {"r": Free(0.5)}

    def test_position_and_style(self):
        d = get(scene(f"{DOT} (dot 'd' (x 3) (fill 'red') (opacity 0.5))"), "d", Motif)
        assert (d.x, d.y, d.fill, d.opacity) == (Free(3.0), Free(0.0), Free("#ff0000ff"), Free(0.5))

    def test_members_inherit_unset_style(self):
        d = get(scene("(motif 'dot' (circle 'c' (stroke 'teal'))) (dot 'd')"), "d", Motif)
        c = member(d, "c", Circle)
        assert (c.fill, c.stroke, c.stroke_width) == (Inherit(), Free("#008080ff"), Inherit())
        assert (c.fill_opacity, c.stroke_opacity) == (Inherit(), Inherit())

    def test_opacity_and_position_are_not_inherited(self):
        d = get(scene(f"{DOT} (dot 'd')"), "d", Motif)
        c = member(d, "c", Circle)
        assert (c.x, c.y, c.opacity) == (Free(0.0), Free(0.0), Free(1.0))

    def test_objects_outside_motifs_do_not_inherit(self):
        assert get(scene("(circle 'c')"), "c", Circle).fill == Free("#000000ff")

    def test_members_are_local_to_each_instance(self):
        scn = scene(f"{DOT} (dot 'a') (dot 'b' (r 3))")
        a, b = get(scn, "a", Motif), get(scn, "b", Motif)
        assert member(a, "c", Circle) is not member(b, "c", Circle)
        assert member(b, "c", Circle).r == Free(3.0)
        assert "c" not in scn

    def test_anonymous_instance(self):
        scn = scene(f"{DOT} (group 'g' (dot _) (dot _))")
        assert all(isinstance(m, Motif) for m in get(scn, "g", Group).members)

    def test_instances_in_repeat(self):
        scn = scene(f"{DOT} (repeat 3 i (dot $'d{{i}}' (x i) (r (+ i 1))))")
        assert member(get(scn, "d2", Motif), "c", Circle).r == Free(3.0)

    @pytest.mark.parametrize(
        "src",
        [
            f"{DOT} (dot 'd' (circle 'z'))",
            f"{DOT} (dot 'd' (nope 1))",
            f"{DOT} (dot 'd' (r 1) (r 2))",
            f"{DOT} (dot 'd' (members 1))",
            f"{DOT} (real 'v' (dot 'd'))",
            "(dot 'd')",
        ],
    )
    def test_invalid(self, src):
        error(src)


class TestNames:
    def test_members_refer_to_each_other_by_bare_name(self):
        src = "(motif 'dot' (circle 'c' (r 2)) (circle 'e' (r c.r))) (dot 'd')"
        e = member(get(scene(src), "d", Motif), "e", Circle)
        assert e.r == Bound(n("c", "r"))

    def test_local_member_shadows_a_global(self):
        src = "(text 'c' 'hi') (motif 'dot' (circle 'c') (circle 'e' (r c.r))) (dot 'd')"
        e = member(get(scene(src), "d", Motif), "e", Circle)
        assert e.r == Bound(n("c", "r"))

    def test_param_shadows_a_global(self):
        src = f"(text 'r' 'hi') {DOT} (dot 'd')"
        assert member(get(scene(src), "d", Motif), "c", Circle).r == Free(1.0)

    def test_body_sees_globals(self):
        src = "(real 'k' 2) (motif 'dot' (circle 'c' (r k))) (dot 'd')"
        assert member(get(scene(src), "d", Motif), "c", Circle).r == Bound(n("k"))

    def test_no_forward_references_in_the_body(self):
        error("(motif 'dot' (circle 'e' (r c.r)) (circle 'c')) (dot 'd')", match="c")

    def test_body_does_not_see_the_instantiation_site(self):
        error("(motif 'dot' (circle 'c' (r i)))", match="i")

    def test_members_of_a_group_in_the_body_are_local(self):
        src = "(motif 'pair' (group 'g' (circle 'a')) (circle 'b' (r a.r))) (pair 'p')"
        p = get(scene(src), "p", Motif)
        assert set(local_names(p)) == {"g", "a", "b"}

    def test_referencing_a_body_member_moves_it(self):
        p = get(scene("(motif 'pair' (circle 'a') (group 'g' a)) (pair 'p')"), "p", Motif)
        assert [m.name for m in p.members] == ["g"]

    def test_one_parent_in_the_body(self):
        error("(motif 'pair' (circle 'a') (group 'g' a) (group 'h' a))", match="'a'")

    def test_read_params_from_outside(self):
        scn = scene(f"{DOT} (dot 'd') (circle 'e' (r d.r))")
        assert get(scn, "e", Circle).r == Bound(n("d", "r"))

    def test_read_members_from_outside(self):
        scn = scene(f"{DOT} (dot 'd') (circle 'e' (r d.c.r))")
        assert get(scn, "e", Circle).r == Bound(n("d", "c", "r"))

    @pytest.mark.parametrize("expr", ["d.nope", "d.c.nope", "(text 't' d.r)"])
    def test_invalid_reads(self, expr):
        src = f"{DOT} (dot 'd') "
        error(src + (expr if expr.startswith("(") else f"(circle 'e' (r {expr}))"))

    def test_nesting(self):
        src = (
            "(motif 'inner' (circle 'c'))"
            " (motif 'outer' (inner 'i' (x 1)))"
            " (outer 'o' (x 2)) (circle 'e' (r o.i.c.x))"
        )
        scn = scene(src)
        i = member(get(scn, "o", Motif), "i", Motif)
        assert i.kind == "inner"
        assert get(scn, "e", Circle).r == Bound(n("o", "i", "c", "x"))

    def test_canvas_shows_instances_and_their_members(self):
        scn = scene(f"{DOT} (dot 'd') (canvas 'cnv' d d.c)")
        d = get(scn, "d", Motif)
        assert scn.views[0].members == [d, member(d, "c", Circle)]


def ev_of(src):
    scn = scene(src)
    return scn, Evaluator(scn, random.Random(0))


class TestEvaluation:
    def test_bound_param(self):
        scn, ev = ev_of(f"(real 'k' 2.5) {DOT} (dot 'd' (r k))")
        d = get(scn, "d", Motif)
        assert ev.value(d, "r") == 2.5
        assert ev.value(member(d, "c", Circle), "r") == 2.5

    def test_instances_are_independent(self):
        scn, ev = ev_of(f"(real 'k' 2.5) {DOT} (dot 'a' (r k)) (dot 'b')")
        a, b = get(scn, "a", Motif), get(scn, "b", Motif)
        assert ev.value(member(a, "c", Circle), "r") == 2.5
        assert ev.value(member(b, "c", Circle), "r") == 1.0

    def test_read_param_from_outside(self):
        scn, ev = ev_of(f"(real 'k' 2.5) {DOT} (dot 'd' (r k)) (real 'v' d.r)")
        assert ev.value(scn["v"], "value") == 2.5

    def test_inside_the_body_coordinates_are_local(self):
        src = "(motif 'dot' (circle 'c' (x 1)) (circle 'e' (y c.x))) (dot 'd' (x 3))"
        scn, ev = ev_of(src)
        assert ev.value(member(get(scn, "d", Motif), "e", Circle), "y") == 1.0

    def test_from_outside_coordinates_are_scene_coordinates(self):
        src = "(motif 'dot' (circle 'c' (x 1))) (dot 'd' (x 3) (y 4)) (real 'v' d.c.x)"
        scn, ev = ev_of(src)
        assert ev.value(scn["v"], "value") == 4.0

    def test_nested_offsets_add_up(self):
        src = (
            "(motif 'inner' (circle 'c' (x 1)))"
            " (motif 'outer' (inner 'i' (x 10)))"
            " (outer 'o' (x 100)) (real 'v' o.i.c.x) (real 'w' o.i.x)"
        )
        scn, ev = ev_of(src)
        assert (ev.value(scn["v"], "value"), ev.value(scn["w"], "value")) == (111.0, 110.0)

    def test_dist_uses_scene_coordinates(self):
        src = "(motif 'dot' (circle 'e' (x 1))) (circle 'g0' (x 10)) (dot 'd' (x 3))"
        scn, ev = ev_of(src + " (real 'v' (dist d.e g0))")
        assert ev.value(scn["v"], "value") == 6.0
        assert ev.point(member(get(scn, "d", Motif), "e", Circle)) == (4.0, 0.0)

    def test_style_is_inherited(self):
        src = "(motif 'dot' (circle 'c') (circle 'e' (fill 'blue'))) (dot 'd' (fill 'red'))"
        scn, ev = ev_of(src)
        d = get(scn, "d", Motif)
        assert ev.value(member(d, "c", Circle), "fill") == "#ff0000ff"
        assert ev.value(member(d, "e", Circle), "fill") == "#0000ffff"

    def test_style_is_inherited_through_nesting_and_defaults_at_the_top(self):
        src = (
            "(motif 'inner' (circle 'c'))"
            " (motif 'outer' (inner 'i'))"
            " (outer 'a' (stroke 'teal')) (outer 'b')"
        )
        scn, ev = ev_of(src)
        ca = member(member(get(scn, "a", Motif), "i", Motif), "c", Circle)
        cb = member(member(get(scn, "b", Motif), "i", Motif), "c", Circle)
        assert ev.value(ca, "stroke") == "#008080ff"
        assert ev.value(cb, "stroke") == "none"


def drawn(src):
    ((_, ax),) = render(scene(src), random.Random(0))
    return ax


def center(artist, ax):
    return tuple((artist.get_transform() - ax.transData).transform((0, 0)))


class TestDrawing:
    def test_members_are_drawn_at_scene_coordinates(self):
        ax = drawn("(motif 'dot' (circle 'c' (x 1))) (dot 'd' (x 3) (y 4)) (canvas 'cnv' d)")
        (circle,) = ax.patches
        assert center(circle, ax) == pytest.approx((4, 4))

    def test_a_member_shown_directly(self):
        ax = drawn("(motif 'dot' (circle 'c' (x 1))) (dot 'd' (x 3)) (canvas 'cnv' d.c)")
        (circle,) = ax.patches
        assert center(circle, ax) == pytest.approx((4, 0))

    def test_inherited_fill(self):
        ax = drawn("(motif 'dot' (circle 'c')) (dot 'd' (fill 'red')) (canvas 'cnv' d)")
        (circle,) = ax.patches
        assert circle.get_facecolor() == to_rgba("red")

    def test_opacity_multiplies(self):
        src = "(motif 'dot' (circle 'c' (opacity 0.5))) (dot 'd' (opacity 0.5)) (canvas 'cnv' d)"
        (circle,) = drawn(src).patches
        assert circle.get_facecolor()[3] == pytest.approx(0.25)

    def test_text_member(self):
        ax = drawn("(motif 'lbl' (text 't' 'hi' (x 1))) (lbl 'l' (x 2)) (canvas 'cnv' l)")
        (text,) = ax.patches
        assert text.get_label() == "hi"
        assert center(text, ax) == pytest.approx((3, 0))
