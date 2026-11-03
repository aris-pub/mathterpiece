"""Variants: a type of shape that refines one shape type (docs/type-system.md 5.e; docs/mtpc.md
"Objects"), and variables that hold shapes (type-system.md 6)."""

from helpers import error, model

from mathterpiece.types import Interface, ShapeT, fits

BAR = "(variant bar ((real p 0 (>= 0))) (rect_ (width 0.8) (y 0) (height (* 5 p))))"
DIAL = "(motif dial (real t 0.5) (circle face (r 1)))"


class TestVariants:
    def test_an_instance_is_its_base_shape(self):
        m = model(f"{BAR} (scene s (bar b1 (x 2) (p 0.4)))")
        b = m.get("b1")
        assert (b.kind, b.of) == ("rect", "bar")
        assert b.attrs["x"].value == 2
        assert b.attrs["p"].value == 0.4
        assert b.attrs["width"].value == 0.8

    def test_the_body_reads_the_parameters(self):
        m = model(f"{BAR} (scene s (bar b1 (p 0.4)))")
        assert (m.id("b1"), "p") in m.get("b1").attrs["height"].deps

    def test_what_the_body_sets_is_fixed(self):
        b = model(f"{BAR} (scene s (bar b1))").get("b1")
        assert b.attrs["width"].fixed and b.attrs["y"].fixed and b.attrs["height"].fixed
        assert not b.attrs["x"].fixed
        error(f"{BAR} (scene s (bar b2 (width 2)))", "a bar's width is fixed")

    def test_pos_is_fixed_when_y_is(self):
        error(f"{BAR} (scene s (bar b2 (pos [1 1])))", "a bar's y is fixed")

    def test_a_variant_is_accepted_where_its_base_is(self):
        m = model(BAR)
        assert fits(m.types["bar"], ShapeT("rect"))
        assert not fits(ShapeT("rect"), m.types["bar"])
        assert fits(m.types["bar"], Interface("positioned"))

    def test_a_variant_of_a_variant(self):
        m = model(f"{BAR} (variant wide (real q 1) (bar_ (x q))) (scene s (wide w (p 1)))")
        w = m.get("w")
        assert (w.kind, w.of) == ("rect", "wide")
        assert w.attrs["x"].fixed and w.attrs["width"].fixed
        assert fits(m.types["wide"], ShapeT("rect"))

    def test_a_variant_cannot_change_what_its_base_fixed(self):
        error(f"{BAR} (variant w2 (real q 1) (bar_ (width 3)))", "a bar's width is fixed")

    def test_a_variant_of_a_motif(self):
        m = model(f"{DIAL} (variant big (real level 0.8) (dial_ (t level))) (scene s (big g))")
        g = m.get("g")
        assert (g.kind, g.of) == ("instance", "big")
        assert g.attrs["t"].fixed
        assert m.get("g.face").parent == m.id("g")

    def test_only_at_the_top_level(self):
        error(f"(scene s {BAR})", "a variant is declared only at the top level")

    def test_its_body_is_one_shape(self):
        error("(variant v (real p 0) (rect_) (rect_))", "one shape")
        error("(variant v (real p 0) (group_))", "a group has no variants")

    def test_a_parameter_cannot_take_a_base_attributes_name(self):
        error("(variant v (real width 1) (rect_))", "a rect already has 'width'")


class TestShapeVariables:
    def test_a_variable_holding_a_shape(self):
        m = model("(scene s (circle p) (shape sel p))")
        assert m.get("sel").value.expr.args[0] == m.id("p")

    def test_declaring_the_shape_in_place(self):
        m = model("(scene s (shape sel (circle c (r 2))))")
        assert m.get("c").attrs["r"].value == 2
        assert m.get("sel").value.expr.args[0] == m.id("c")

    def test_it_reads_only_what_its_type_lists(self):
        error("(scene s (circle p) (shape sel p) (real k sel.r))", "a shape has no attribute 'r'")
        model("(scene s (circle p) (positioned sel p) (real k sel.x))")


def test_a_variants_positional_value_is_fixed():
    m = model("(func f (int n) $'{n}') (variant label () (text_ (f 1))) (scene s (label l))")
    assert m.get("l").attrs["value"].fixed
