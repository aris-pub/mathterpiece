"""Groups, the scene, positions and frames (docs/type-system.md 5.e and 6; docs/reference.md
"Coordinates" and "The scene and shapes")."""

import pytest

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.types import INT, POINT, REAL, ListT, Maybe, Refine

RADIUS = Refine(REAL, ((">=", 0),))


def model(src):
    return compile_source(src)


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile_source(src)


def attr(src, name, a):
    return model(src).get(name).attrs[a]


def moves(m, *names):
    """The translate and transform attributes of the shapes named."""
    return {(m.id(n), a) for n in names for a in ("translate", "transform")}


class TestGroupArguments:
    # reference.md: on a group, x, y, pos and the paint arguments are written on each member.
    def test_they_reach_every_member(self):
        m = model("(scene s (group g (fill 'red') (x 2) (circle a) (rect b)))")
        assert m.get("a").attrs["fill"].value == m.get("b").attrs["fill"].value == "#ff0000ff"
        assert m.get("a").attrs["x"].value == m.get("b").attrs["x"].value == 2

    def test_through_nested_groups(self):
        m = model("(scene s (group g (opacity 0.5) (group h (circle a))))")
        assert m.get("a").attrs["opacity"].value == 0.5

    def test_pos(self):
        m = model("(scene s (group g (pos [1 2]) (circle a)))")
        assert (m.get("a").attrs["x"].value, m.get("a").attrs["y"].value) == (1, 2)

    def test_a_member_that_gives_its_own_value_keeps_it(self):
        m = model("(scene s (group g (fill 'red') (circle a (fill 'blue')) (circle b)))")
        assert m.get("a").attrs["fill"].value == "#0000ffff"
        assert m.get("b").attrs["fill"].value == "#ff0000ff"

    def test_the_nearest_group_wins(self):
        m = model("(scene s (group g (fill 'red') (group h (fill 'blue') (circle a))))")
        assert m.get("a").attrs["fill"].value == "#0000ffff"

    def test_a_text_takes_no_stroke_from_a_group(self):
        # A stroke would outline a text's letters (reference.md, "The scene and shapes").
        src = "(group g (stroke 'red') (stroke-width 3) (fill 'blue') (text t 'hi') (circle c))"
        m = model(f"(scene s {src})")
        t = m.get("t").attrs
        assert t["stroke"].value is None and t["stroke-width"].value == 1
        assert t["fill"].value == "#0000ffff"
        assert m.get("c").attrs["stroke"].value == "#ff0000ff"

    def test_a_text_keeps_its_own_stroke(self):
        m = model("(scene s (group g (stroke 'red') (text t 'hi' (stroke 'blue'))))")
        assert m.get("t").attrs["stroke"].value == "#0000ffff"

    def test_pos_and_x_meet_coordinate_by_coordinate(self):
        m = model("(scene s (group g (pos [5 6]) (circle a (x 1)) (circle b (pos [1 2]))))")
        assert (m.get("a").attrs["x"].value, m.get("a").attrs["y"].value) == (1, 6)
        assert (m.get("b").attrs["x"].value, m.get("b").attrs["y"].value) == (1, 2)
        m = model("(scene s (group g (pos [5 6]) (group h (x 0) (circle a))))")
        assert (m.get("a").attrs["x"].value, m.get("a").attrs["y"].value) == (0, 6)

    def test_a_member_without_the_attribute(self):
        error("(scene s (group g (x 1) (line l)))", "a line takes no argument 'x'")

    def test_translate_is_the_groups_own(self):
        m = model("(scene s (group g (translate [5 0]) (circle a)))")
        assert m.get("g").attrs["translate"].value == (5, 0)
        assert m.get("a").attrs["translate"].value == (0, 0)


class TestGroupReads:
    def test_length_and_members(self):
        m = model("(scene s (group g (circle a) (circle b)) (int n g.length))")
        assert m.get("n").value.value == 2
        assert m.get("n").type == INT

    def test_a_spread_read(self):
        m = model("(scene s (group g (circle a) (circle b (r 2))) (list rs g.r))")
        e = m.get("rs").value.expr
        assert e.op == "spread"
        assert e.type == Refine(ListT(RADIUS), (("length", 2),))
        assert {(m.id("a"), "r"), (m.id("b"), "r")} <= e.deps

    def test_a_spread_read_needs_every_member_to_have_it(self):
        error("(scene s (group g (circle a) (rect b)) (list rs g.r))", "every member")

    def test_a_member_by_a_position_known_while_drawing(self):
        m = model("(scene s (int k) (group g (circle a) (circle b)) (real|none d g[k].r))")
        e = m.get("d").value.expr
        assert e.type == Maybe(RADIUS)
        assert {(m.id("a"), "r"), (m.id("b"), "r")} <= e.deps

    def test_a_lookup_that_can_never_miss(self):
        src = (
            "(type side string (one-of 'a' 'b'))"
            "(scene s (side k 'a') (group g (circle a) (circle b)) (real d g[k].r))"
        )
        assert model(src).get("d").value.expr.type == RADIUS

    def test_members_of_different_types_meet_at_an_interface(self):
        m = model(
            "(scene s (int k 0 (>= 0) (<= 1)) (group g (circle a) (rect b)) (real|none d g[k].x))"
        )
        # k stays within the two members, so the read is never none (mtp-2uae).
        assert m.get("d").value.expr.type == REAL
        error(
            "(scene s (int k) (group g (circle a) (rect b)) (real|none d g[k].r))",
            "no attribute 'r'",
        )


class TestSceneReads:
    def test_background_and_length(self):
        m = model("(scene s (background 'white') (circle a) (circle b) (int n s.length))")
        assert m.get("n").value.value == 2

    def test_no_spreading(self):
        error("(scene s (circle a) (list rs s.r))", "a scene has no attribute 'r'")

    def test_members_by_name(self):
        m = model("(scene s (circle a (r 3)) (real d (. (. s 'a') r)))")
        assert (m.id("a"), "r") in m.get("d").value.deps


class TestPositions:
    # reference.md: a line's position is its midpoint, a triangle's its centroid.
    def test_a_lines_midpoint(self):
        m = model("(scene s (line l (from [0 0]) (to [4 2])) (real d l.x))")
        e = m.get("d").value.expr
        assert e.op == "/"
        assert {(m.id("l"), "from"), (m.id("l"), "to")} <= e.deps

    def test_a_triangles_centroid(self):
        m = model("(scene s (triangle t (a [0 0]) (b [3 0]) (c [0 3])) (point p t.pos))")
        assert {(m.id("t"), c) for c in "abc"} <= m.get("p").value.deps

    def test_a_line_is_never_given_a_position(self):
        error("(scene s (line l (x 1)))", "a line takes no argument 'x'")


class TestFrames:
    # reference.md "Coordinates": a read converts through every transform that applies to the
    # shape read but not to the attribute reading it.
    def test_a_sibling_reads_in_the_groups_frame(self):
        m = model("(scene s (group g (translate [5 0]) (circle p (x 1)) (circle q (x p.x))))")
        e = m.get("q").attrs["x"].expr
        assert e.args == (m.id("p"), "x", m.id("g"))
        assert e.deps == {(m.id("p"), "x")} | moves(m, "p")

    def test_outside_the_group_the_groups_transforms_count(self):
        m = model("(scene s (group g (translate [5 0]) (circle p (x 1))) (circle q (x p.x)))")
        e = m.get("q").attrs["x"].expr
        assert e.args == (m.id("p"), "x", None)
        assert e.deps == {(m.id("p"), "x")} | moves(m, "p", "g")

    def test_a_variable_is_never_converted(self):
        m = model("(scene s (real k 1) (group g (circle p (x k))))")
        assert m.get("p").attrs["x"].expr.deps == {(m.id("k"), None)}


class TestPositional:
    # syntax.md section 8: a positional argument is recognized by where it is.
    def test_a_texts_value_may_be_a_call(self):
        m = model("(func f (int n) $'{n}') (int k) (scene s (text t (f k)))")
        assert m.get("t").attrs["value"].expr.op == "call"

    def test_an_argument_first_is_still_an_argument(self):
        m = model("(scene s (text t (x 1)))")
        assert (m.get("t").attrs["x"].value, m.get("t").attrs["value"].value) == (1, "")


def test_a_groups_pos_spreads():
    m = model("(scene s (group g (circle a) (circle b)) (list ps g.pos))")
    e = m.get("ps").value.expr
    assert e.op == "spread" and e.type.base == ListT(POINT)


class TestNoName:
    # syntax.md "Names": (head_ …) is (head none …); an object given none as its name has a name
    # attribute that is none.
    def test_none_declares_something_with_no_name(self):
        m = compile_source("(scene s (circle none (r 2)) (circle_ (r 3)))")
        circles = [o for o in m.objects if o.kind == "circle"]
        assert [c.name for c in circles] == [None, None]

    def test_an_unnamed_objects_name_is_none(self):
        m = compile_source(
            "(scene s (group g (circle_) (circle b)) (string|none n g[0].name)"
            " (string|none nb g[1].name))"
        )
        assert m.get("n").value.value is None
        assert m.get("nb").value.value == "b"
