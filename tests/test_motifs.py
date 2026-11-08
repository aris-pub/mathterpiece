"""Motifs: types of shape made of several shapes, with parameters (docs/type-system.md 5.e;
docs/reference.md "Types" and "The scene and shapes"; docs/mtpc.md "Objects")."""

from helpers import doc, error, model

from mathterpiece.compiler import compile_source
from mathterpiece.types import BOOL, REAL, Interface, ShapeT, fits

DIAL = (
    "(motif dial ((real t 0.5 (>= 0) (<= 1)) (color tint 'red'))"
    "  (circle face (r 1) (fill tint))"
    "  (real angle (* 360 t))"
    "  (line hand (to [face.r 0])))"
)


class TestDeclaring:
    def test_a_motif_is_a_type_of_shape(self):
        m = model(DIAL)
        assert m.types["dial"] == ShapeT("dial")
        assert [p.name for p in m.motifs["dial"].params] == ["t", "tint"]

    def test_one_parameter_alone(self):
        m = model("(motif dot (real k 1) (circle c (r 1)))")
        assert [p.name for p in m.motifs["dot"].params] == ["k"]

    def test_only_at_the_top_level(self):
        error(f"(scene s {DIAL})", "a motif is declared only at the top level")

    def test_a_parameter_cannot_take_a_shape_arguments_name(self):
        error("(motif m (real x 0) (circle c))", "every motif instance already has 'x'")

    def test_the_body_declares_only_bound_variables(self):
        error("(motif m (real t 0) (real k 1) (circle c))", "only bound variables")


class TestInstances:
    def test_an_instance(self):
        m = model(f"{DIAL} (scene s (dial d1 (t 0.2)))")
        d = m.get("d1")
        assert (d.kind, d.of, d.type) == ("instance", "dial", ShapeT("dial"))
        assert d.attrs["t"].value == 0.2
        assert d.attrs["tint"].value == "#ff0000ff"

    def test_its_members_are_named_through_it(self):
        m = model(f"{DIAL} (scene s (dial d1) (dial d2))")
        assert m.get("d1.face").parent == m.id("d1")
        assert [m.objects[i].name for i in m.get("d1").members] == ["face", "hand"]

    def test_the_body_reads_its_parameters(self):
        m = model(f"{DIAL} (scene s (dial d1 (tint 'blue')))")
        assert m.get("d1").attrs["tint"].value == "#0000ffff"
        assert m.get("d1.face").attrs["fill"].deps == {(m.id("d1"), "tint")}

    def test_a_parameter_is_checked_against_its_constraints(self):
        error(f"{DIAL} (scene s (dial d1 (t 2)))", r"2 breaks \(<= 1\)")

    def test_bound_variables_are_attributes_of_the_instance(self):
        m = model(f"{DIAL} (scene s (dial d1) (real a d1.angle))")
        assert (m.id("d1"), "angle") in m.get("a").value.deps
        assert m.get("d1").attrs["angle"].bound

    def test_members_are_read_through_the_instance(self):
        m = model(f"{DIAL} (scene s (dial d1) (real r d1.face.r))")
        assert (m.id("d1.face"), "r") in m.get("r").value.deps

    def test_an_unknown_argument(self):
        error(f"{DIAL} (scene s (dial d1 (width 2)))", "a dial takes no argument 'width'")

    def test_an_instance_takes_no_members(self):
        error(f"{DIAL} (scene s (dial d1 (circle c)))", "takes no members")

    def test_anonymous_instances_still_work(self):
        m = model(f"{DIAL} (scene s (dial_) (dial_))")
        assert len([o for o in m.objects if o.kind == "instance"]) == 2

    def test_self(self):
        m = model("(motif m (real k 1 (>= 0)) (circle c (r self.k))) (scene s (m a))")
        assert (m.id("a"), "k") in m.get("a.c").attrs["r"].deps
        error("(scene s (circle c (r self.r)))", "self is used only in a motif's body")

    def test_motifs_inside_motifs(self):
        m = model(
            f"{DIAL} (motif pair (real u 0 (>= 0) (<= 1)) (dial left (t u)) (dial right))"
            "(scene s (pair p))"
        )
        assert m.get("p.left.face").parent == m.id("p.left")


class TestShapeArguments:
    # reference.md: x and y move the instance's frame; like a group, it gives its members
    # defaults in (defaults …).
    def test_position_and_transforms(self):
        m = model(f"{DIAL} (scene s (dial d1 (pos [2 3]) (translate [1 0])))")
        d = m.get("d1")
        assert (d.attrs["x"].value, d.attrs["y"].value, d.attrs["translate"].value) == (
            2,
            3,
            (1, 0),
        )

    def test_a_members_read_from_outside_converts_through_the_instance(self):
        m = model(f"{DIAL} (scene s (dial d1) (real k d1.face.x))")
        d = m.id("d1")
        assert {(d, "x"), (d, "y"), (d, "translate"), (d, "transform")} <= m.get("k").value.deps

    def test_defaults_for_the_members(self):
        # mtp-4cw5: an instance behaves like a group: its members take its defaults, and a
        # member that gives its own value keeps it.
        m = model(
            "(motif m (real u 0) (circle a) (circle b (stroke 'blue')))"
            "(scene s (m i (defaults (stroke 'red'))))"
        )
        assert m.get("i.a").attrs["stroke"].value == "#ff0000ff"
        assert m.get("i.b").attrs["stroke"].value == "#0000ffff"
        assert "stroke" not in m.get("i").attrs

    def test_opacity_is_each_members(self):
        m = model("(motif m (real u 0) (circle a)) (scene s (m i (defaults (opacity 0.5))))")
        assert m.get("i.a").attrs["opacity"].value == 0.5

    def test_no_fill_of_its_own(self):
        error(
            "(motif m (real u 0) (circle a)) (scene s (m i (fill 'red')))", "give it in \\(defaults"
        )

    def test_reading_and_writing_go_to_every_member(self):
        m = model(
            "(motif m (real u 0) (circle a) (circle b)) (scene s (m i))"
            " (list fs i.fill) (button go (animation (move i.fill (to 'red') (duration 1))))"
        )
        deps = m.get("fs").value.expr.deps
        assert {(m.id("i.a"), "fill"), (m.id("i.b"), "fill")} <= deps

    def test_a_write_reaches_members_inside_a_group(self):
        m = model(
            "(motif m (real u 0) (group inner (circle a) (circle b))) (scene s (m i))"
            " (button go (animation (move i.fill (to 'red') (duration 1))))"
        )
        animation = m.objects[m.get("go").data["animation"]]
        assert animation.data["steps"][1] == (m.id("i"), "fill")

    def test_a_groups_defaults_reach_an_instances_members(self):
        m = model(
            "(motif m (real u 0) (circle a)) (scene s (group g (defaults (fill 'red')) (m i)))"
        )
        assert m.get("i.a").attrs["fill"].value == "#ff0000ff"


class TestTypes:
    def test_an_instance_is_a_positioned_shape(self):
        assert fits(ShapeT("dial"), Interface("shape"))
        assert fits(ShapeT("dial"), Interface("positioned"))

    def test_reading_x(self):
        m = model(f"{DIAL} (scene s (dial d1 (x 2)) (real k d1.x))")
        assert m.get("k").value.expr.type == REAL


class TestNoParameters:
    def test_a_motif_with_no_parameters(self):
        m = model("(motif dot () (circle c (r 2))) (scene s (dot d))")
        assert m.motifs["dot"].params == ()
        assert m.get("d.c").attrs["r"].value == 2

    def test_a_variant_with_no_parameters(self):
        m = model("(variant unit () (circle_ (r 1))) (scene s (unit u))")
        assert m.get("u").attrs["r"].fixed


class TestBodyLists:
    # type-system.md "Known lengths": a variable bound to a list keeps its length, in a motif's
    # body as in the scene.
    def test_a_bound_list_in_a_body_keeps_its_length(self):
        # So v[i] is never none, and each radius is a real.
        m = compile_source(
            "(motif m ((real a 1)) (list v [a a]) (foreach i 2 (circle_ (r (+ 1 (abs v[i]))))))"
            " (scene s (m m1))"
        )
        circles = [o for o in m.objects if o.kind == "circle"]
        assert len(circles) == 2
        for c in circles:
            r = c.attrs["r"].expr
            assert r is not None and r.type == REAL

    def test_a_folded_value_in_a_body_is_allowed(self):
        # Known when compiling, it is free with a const constraint, which no writer may write.
        m = compile_source(
            "(motif m ((real a 1 (const))) (real twice (* 2 a)) (circle_ (r twice)))"
            " (scene s (m m1))"
        )
        (c,) = [o for o in m.objects if o.kind == "circle"]
        assert not c.attrs["r"].bound and c.attrs["r"].value == 2


class TestOptionalInstances:
    # An instance declared T|none so that an exists-when can hide it (mtp-3f9l). Its parameters
    # may be none as its attributes may, but one given a value that is never none keeps its own
    # type, as a shape's attribute does.
    SRC = (
        "(int n 3) (motif dot ((bool shown true) (real size 1 (>= 0))) (circle_ (r size)))\n"
        "(scene s (foreach i 5 (dot|none #'d-{i}' (shown (< i n))) (exists-when #'d-{i}' (< i n))))"
    )

    def test_a_parameter_given_a_value_never_none_keeps_its_type(self):
        m = compile_source(self.SRC)
        dots = [o for o in m.objects if o.kind == "instance"]
        assert len(dots) == 5
        for d in dots:
            assert d.attrs["shown"].type == BOOL

    def test_its_document_is_written(self):
        d = doc(self.SRC)
        assert len([o for o in d["objects"] if o["kind"] == "instance"]) == 5

    def test_its_body_reads_its_parameters_as_given(self):
        # The body is drawn only while the instance exists, so a parameter that is never none
        # is never none there either.
        compile_source(
            "(int n 3) (motif dot ((bool wide false)) (circle_ (r (if wide 2 1))))\n"
            "(scene s (foreach i 5 (dot|none #'d-{i}' (wide (< i 2)))"
            " (exists-when #'d-{i}' (< i n))))"
        )
