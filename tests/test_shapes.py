"""Groups, the scene, positions and frames (docs/type-system.md 5.e and 6; docs/reference.md
"Coordinates" and "The scene and shapes")."""

from helpers import bound, doc, error, model
from mtpc_check import errors

from mathterpiece.compiler import compile_source
from mathterpiece.types import INT, POINT, REAL, ListT, Maybe, Refine

RADIUS = Refine(REAL, ((">=", 0),))


def attr(src, name, a):
    return model(src).get(name).attrs[a]


def moves(m, *names):
    """The translate and transform attributes of the shapes named."""
    return {(m.id(n), a) for n in names for a in ("translate", "transform")}


class TestGroupArguments:
    # reference.md: on a group, x, y, pos and fill, stroke and the like are written on each member.
    def test_they_reach_every_member(self):
        m = model("(scene s (group g (defaults (fill 'red')) (circle a) (rect b)))")
        assert m.get("a").attrs["fill"].value == m.get("b").attrs["fill"].value == "#ff0000ff"

    def test_through_nested_groups(self):
        m = model("(scene s (group g (defaults (opacity 0.5)) (group h (circle a))))")
        assert m.get("a").attrs["opacity"].value == 0.5

    def test_no_position_in_defaults(self):
        # The author, 2026-11-03: x, y and pos are not defaults; a group is moved by translate.
        for attr in ("(x 1)", "(y 1)", "(pos [1 2])"):
            error(f"(scene s (group g (defaults {attr}) (circle a)))", "not x, y or pos")

    def test_a_member_that_gives_its_own_value_keeps_it(self):
        m = model("(scene s (group g (defaults (fill 'red')) (circle a (fill 'blue')) (circle b)))")
        assert m.get("a").attrs["fill"].value == "#0000ffff"
        assert m.get("b").attrs["fill"].value == "#ff0000ff"

    def test_the_nearest_group_wins(self):
        m = model(
            "(scene s (group g (defaults (fill 'red')) (group h (defaults (fill 'blue'))"
            " (circle a))))"
        )
        assert m.get("a").attrs["fill"].value == "#0000ffff"

    def test_a_text_takes_no_stroke_from_a_group(self):
        # A stroke would outline a text's letters (reference.md, "The scene and shapes").
        src = (
            "(group g (defaults (stroke 'red') (stroke-width 3) (fill 'blue')) (text t 'hi')"
            " (circle c))"
        )
        m = model(f"(scene s {src})")
        t = m.get("t").attrs
        assert t["stroke"].value is None and t["stroke-width"].value == 1
        assert t["fill"].value == "#0000ffff"
        assert m.get("c").attrs["stroke"].value == "#ff0000ff"

    def test_a_text_keeps_its_own_stroke(self):
        m = model("(scene s (group g (defaults (stroke 'red')) (text t 'hi' (stroke 'blue'))))")
        assert m.get("t").attrs["stroke"].value == "#0000ffff"

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


class TestGroupPositionsInRange:
    # mtp-2uae: as for lists, a member read at a position whose range lies within the group's
    # members is never none.
    G = "(scene s (group g (circle a) (circle b) (circle c)) (point p g[i].pos))"

    def test_a_position_in_range(self):
        m = model(f"(int i 0 (>= 0) (<= 2)) {self.G}")
        assert m.get("p").value.bound

    def test_a_position_that_may_be_out_of_range(self):
        error(f"(int i 0 (>= 0) (<= 3)) {self.G}", "may be none")


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


class TestDefaults:
    # mtp-xj5b: (defaults …) holds the values a group's members take when they give none of
    # their own; a group's translate and transform stay its own.
    def test_fill_and_stroke_for_the_members(self):
        m = model(
            "(scene s (group g (defaults (fill 'red') (stroke-width 2)) (circle c) (circle"
            " d (fill 'blue'))))"
        )
        assert m.get("c").attrs["fill"].value == "#ff0000ff"
        assert m.get("c").attrs["stroke-width"].value == 2
        assert m.get("d").attrs["fill"].value == "#0000ffff"

    def test_text_settings_for_the_texts(self):
        m = model(
            "(font note (size 9))"
            " (scene s (group g (defaults (font note) (halign 'middle') (fill 'red'))"
            " (text t 'a') (circle c)))"
        )
        assert m.get("t").attrs["halign"].value == "middle"
        assert m.get("c").attrs["fill"].value == "#ff0000ff"

    def test_a_group_has_no_fill_of_its_own(self):
        error("(scene s (group g (fill 'red') (circle c)))", "give it in \\(defaults")

    def test_translate_stays_the_groups_own(self):
        m = model("(scene s (group g (translate [1 0]) (defaults (fill 'red')) (circle c)))")
        assert m.get("g").attrs["translate"].value == (1, 0)


class TestExistsWhen:
    # mtp-b9g0: (exists-when name bool), after the shape it names, says when it exists in the
    # scene; each must be declared T|none, so whatever reads it handles none.
    def test_a_condition_for_a_shape(self):
        m = model("(scene s (real k 0) (circle|none c (r 1)) (exists-when c (> k 0)))")
        exists = m.get("c").attrs["exists"]
        assert exists.bound and (m.id("k"), None) in exists.deps

    def test_in_a_group_and_a_foreach(self):
        m = model(
            "(scene s (real k 0) (group g (foreach i 3 (circle|none (name $'c{i}') (r 1))"
            " (exists-when (name $'c{i}') (< i k)))))"
        )
        assert m.get("c2").attrs["exists"].bound

    def test_in_a_motif(self):
        m = model(
            "(motif dot ((real t 1)) (circle|none face (r 1)) (exists-when face (> t 0)))"
            " (scene s (dot d))"
        )
        assert (m.id("d"), "t") in m.get("d.face").attrs["exists"].deps

    def test_the_shape_must_be_declared_t_or_none(self):
        error("(scene s (real k 0) (circle c (r 1)) (exists-when c (> k 0)))", "circle\\|none")

    def test_it_comes_after_the_shape(self):
        error(
            "(scene s (real k 0) (exists-when c (> k 0)) (circle|none c (r 1)))", "unknown name 'c'"
        )

    def test_once_per_shape(self):
        error(
            "(scene s (real k 0) (circle|none c (r 1)) (exists-when c (> k 0))"
            " (exists-when c (> k 1)))",
            "given twice",
        )

    def test_one_shape_then_its_condition(self):
        error(
            "(scene s (real k 0) (circle|none a) (circle|none b) (exists-when a b (> k 0)))",
            "exists-when is \\(exists-when shape condition\\)",
        )

    def test_the_members_of_a_container_that_may_not_exist_may_not_either(self):
        # Non-existence cascades from a container to its members.
        src = "(scene s (real k 0) (group|none g (circle a (r 1))) (exists-when g (> k 0)) {})"
        assert isinstance(model(src.format("(real|none r a.r)")).get("a").type, Maybe)
        error(src.format("(real r a.r)"), "may be none")

    def test_the_compiled_file(self):
        d = doc("(scene s (real k 0) (circle|none c (r 1)) (exists-when c (> k 0)))")
        assert errors(d) == []
        assert d["objects"][d["names"]["c"]]["attrs"]["exists"]["bound"][0] == "builtin"


class TestSceneTransform:
    # mtp-y0gh: a scene takes a transform, such as (scale 1 -1) for y pointing down.
    def test_a_scene_takes_a_transform(self):
        m = model("(scene s (transform (scale 1 -1)) (circle c))")
        assert m.get("s").attrs["transform"].value == (1, 0, 0, -1, 0, 0)

    def test_by_default_none(self):
        assert model("(scene s (circle c))").get("s").attrs["transform"].value == (1, 0, 0, 1, 0, 0)


class TestClip:
    # mtp-un2f, the author 2026-11-03: (clip shape) on a container draws its members only inside
    # the shape, which is never drawn; it is bound like any shape, its box cuts the container's,
    # and the pointer does not reach what it cuts off.
    SRC = (
        "(real w 4) (scene s (group g (clip (rect window (width w) (height 2)))"
        " (circle a (r 3)) (circle b)))"
    )

    def test_the_clip_is_not_a_member(self):
        m = model(self.SRC)
        g = m.get("g")
        assert g.data["clip"] == m.id("window")
        assert m.id("window") not in g.members and len(g.members) == 2

    def test_it_lives_in_the_containers_frame(self):
        m = model(self.SRC)
        assert m.get("window").parent == m.id("g")

    def test_it_is_bound_read_and_moved_like_any_shape(self):
        m = model(self.SRC + " (real v window.width)")
        assert m.get("window").attrs["width"].bound
        assert bound(self.SRC + " (real v window.width)").op == "read"
        model(self.SRC + " (animation grow (move window.height (to 8) (duration 1)))")

    def test_a_clip_with_no_name(self):
        m = model("(scene s (group g (clip (circle_ (r 2))) (circle a (r 3))))")
        assert m.get("g").data["clip"] not in m.get("g").members

    def test_the_shapes_it_may_be(self):
        for shape in ("(circle_)", "(ellipse_)", "(triangle_)", "(rect_)"):
            model(f"(scene s (group g (clip {shape}) (circle a)))")
        for shape in ("(text_ 'x')", "(group_ (circle_))", "(line_)"):
            error(f"(scene s (group g (clip {shape}) (circle a)))", "a clip is a circle")
        error("(scene s (group g (clip 3) (circle a)))", "a clip is a circle")

    def test_it_always_exists(self):
        error(
            "(scene s (group g (clip (rect|none window)) (circle a)))",
            "a clip always exists",
        )

    def test_once_and_before_the_body(self):
        error("(scene s (group g (clip (rect_)) (clip (rect_)) (circle a)))", "given twice")
        error("(scene s (group g (circle a) (clip (rect_))))", "before the group's body")

    def test_a_row_lays_out_its_members_only(self):
        m = model("(scene s (row r (clip (rect_ (width 3))) (circle a) (circle b)))")
        assert len(m.get("r").members) == 2

    def test_a_containers_box_reads_its_clip(self):
        # So a shape placed against the container moves when the clip changes.
        m = model(self.SRC.replace("(circle b)))", "(circle b))") + " (circle c (pos (top g))))")
        deps = m.get("c").attrs["x"].expr.deps
        assert (m.id("window"), "height") in deps

    def test_a_motif_instance_too(self):
        m = model(
            "(motif dot () (circle c (r 3))) (scene s (dot d (clip (rect window (width 2)))))"
            " (real v window.width)"
        )
        d = m.get("d")
        assert d.data["clip"] == m.id("window") and m.id("window") not in d.members
        assert m.get("window").parent == m.id("d")
        d = doc("(motif dot () (circle c)) (scene s (dot d (clip (rect_))))")
        assert "clip" in d["objects"][d["names"]["d"]]

    def test_a_canvas_does_not_show_it(self):
        error(self.SRC + " (canvas v window)", "never drawn")

    def test_the_compiled_file(self):
        d = doc(self.SRC)
        assert errors(d) == []
        g = d["objects"][d["names"]["g"]]
        assert g["clip"] == d["names"]["window"]
        assert d["names"]["window"] not in g["members"]


def test_error_messages_name_things_rightly():
    # Found 2026-11-04 checking the docs against the code (mtp-pjzt).
    error(
        "(motif m () (circle c)) (scene s (m i)) (real v i.zz)", "an instance has no attribute 'zz'"
    )
    error("(scene s (group g (clip (line_)) (circle a)))", "rect, ellipse, triangle or polygon")
