"""(parametric N (for t LO HI) EXPR item…) is sugar for a polyline through S points of EXPR, t
from LO to HI, S being 361 unless (samples S) is given (the author, 2026-11-16)."""

from helpers import error, model

CURVE = "(scene s (parametric c (for t 0 360) [(cosd t) (sind t)] {} (stroke 'teal')))"


def points(src, name="c"):
    return model(src).get(name).attrs["points"].value


class TestParametric:
    def test_it_is_a_polyline_through_361_points(self):
        m = model(CURVE.format(""))
        c = m.get("c")
        assert c.kind == "polyline"
        assert len(c.attrs["points"].value) == 361
        assert c.attrs["stroke"].value is not None

    def test_the_points_are_the_expression_at_even_steps(self):
        ps = points(CURVE.format(""))
        assert ps[0] == (1, 0) or tuple(ps[0]) == (1.0, 0.0)
        x, y = ps[90]
        assert abs(x) < 1e-12 and abs(y - 1) < 1e-12

    def test_samples(self):
        assert len(points(CURVE.format("(samples 5)"))) == 5

    def test_unnamed(self):
        m = model("(scene s (parametric_ (for t 0 1) [t (* t t)] (samples 3)))")
        assert any(o.kind == "polyline" for o in m.objects)

    def test_it_follows_a_variable(self):
        src = "(real k 2) (scene s (parametric c (for t 0 1) [t (* k t)] (samples 2)))"
        assert model(src).get("c").attrs["points"].bound

    def test_errors(self):
        error("(scene s (parametric c [0 0]))", "a parametric curve is")
        error("(scene s (parametric c (t 0 1) [t t]))", r"\(for t from to\)")
