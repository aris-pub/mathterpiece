import random

import pytest

from mathterpiece.parser import Parser
from mathterpiece.scene import Circle, Group, Real, Text
from mathterpiece.views import Canvas


@pytest.fixture
def prs():
    return Parser("")


class TestAtoms:
    def test_int(self, prs):
        assert prs.parse_sexp("3") == 3

    def test_float(self, prs):
        assert prs.parse_sexp("-2.5") == -2.5

    def test_string(self, prs):
        assert prs.parse_sexp("'disk'") == "disk"

    def test_bool(self, prs):
        assert prs.parse_sexp("False") is False

    def test_bound_var_in_fstring(self, prs):
        prs.boundvars["i"] = 7
        assert prs.parse_sexp("f'dot{i}'") == "dot7"

    def test_return_func_defers_evaluation(self, prs):
        func = prs.parse_sexp("x", return_func=True)
        prs.boundvars["x"] = 5
        assert func() == 5


class TestLists:
    def test_list_of_atoms(self, prs):
        assert prs.parse_sexp("[1 2 3]") == [1, 2, 3]

    def test_list_of_strings(self, prs):
        assert prs.parse_sexp("['a' 'b']") == ["a", "b"]

    def test_empty_list(self, prs):
        assert prs.parse_sexp("[]") == []

    def test_list_of_sexps(self, prs):
        res = prs.parse_sexp("[(circle 'a') (circle 'b')]")
        assert [type(o) for o in res] == [Circle, Circle]
        assert [o.name for o in res] == ["a", "b"]


class TestAttrs:
    def test_attrs_stay_unparsed(self, prs):
        assert prs.parse_attrs("(r 1) (x (rand 0 1))") == {"r": "1", "x": "(rand 0 1)"}

    def test_no_attrs(self, prs):
        assert prs.parse_attrs("") == {}


class TestCircle:
    def test_defaults(self, prs):
        c = prs.parse_sexp("(circle 'disk')")
        assert isinstance(c, Circle)
        assert (c.name, c.x, c.y, c.r) == ("disk", 0.0, 0.0, 1.0)
        assert (c.facecolor, c.edgecolor, c.fill) == ("black", "black", True)
        assert (c.linewidth, c.alpha) == (1.0, 1.0)

    def test_given_attrs(self, prs):
        c = prs.parse_sexp(
            "(circle 'c' (r 3.5) (x -5.0) (y 4.0) (edgecolor 'teal')"
            " (facecolor 'red') (linewidth 1.5) (fill False) (alpha 0.25))"
        )
        assert (c.r, c.x, c.y) == (3.5, -5.0, 4.0)
        assert (c.edgecolor, c.facecolor) == ("teal", "red")
        assert (c.linewidth, c.fill, c.alpha) == (1.5, False, 0.25)

    def test_attr_from_expression(self, prs):
        c = prs.parse_sexp("(circle 'c' (r (mult 2 3)))")
        assert c.r == 6

    def test_unknown_attr_raises(self, prs):
        with pytest.raises(TypeError):
            prs.parse_sexp("(circle 'c' (radius 2))")


class TestText:
    def test_literal_value(self, prs):
        t = prs.parse_sexp("(text 'lbl' 'hello' (x 1) (y 2))")
        assert isinstance(t, Text)
        assert (t.name, t.val, t.x, t.y) == ("lbl", "hello", 1, 2)

    def test_value_from_expression(self, prs):
        t = prs.parse_sexp("(text 'lbl' (mult 2 3))")
        assert t.val == 6

    def test_real_value_is_unwrapped(self):
        scn = Parser("(real 'pi' 3.14) (text 'lbl' pi)").parse()
        assert scn["lbl"].val == 3.14


class TestReal:
    def test_value(self, prs):
        r = prs.parse_sexp("(real 'pi' 3.1415926535)")
        assert isinstance(r, Real)
        assert (r.name, r.val) == ("pi", 3.1415926535)

    def test_default(self, prs):
        assert prs.parse_sexp("(real 'zero')").val == 0.0

    def test_value_from_expression(self, prs):
        assert prs.parse_sexp("(real 'six' (mult 2 3))").val == 6


class TestMult:
    def test_numbers(self, prs):
        assert prs.parse_sexp("(mult 2 3 4)") == 24

    def test_single(self, prs):
        assert prs.parse_sexp("(mult 5)") == 5

    def test_nested(self, prs):
        assert prs.parse_sexp("(mult 2 (mult 3 4))") == 24

    def test_unwraps_reals(self):
        scn = Parser("(real 'a' 2) (real 'b' 5) (real 'c' (mult a b 3))").parse()
        assert scn["c"].val == 30

    def test_reads_attributes(self):
        scn = Parser("(circle 'disk' (r 3)) (real 'd' (mult 2 disk.r))").parse()
        assert scn["d"].val == 6


class TestRand:
    def test_range(self, prs):
        random.seed(0)
        vals = [prs.parse_sexp("(rand -10 10)") for _ in range(200)]
        assert all(-10 <= v <= 10 for v in vals)
        assert len(set(vals)) > 1

    def test_default_range(self, prs):
        random.seed(0)
        vals = [prs.parse_sexp("(rand)") for _ in range(200)]
        assert all(0 <= v <= 1 for v in vals)

    def test_seeded_is_reproducible(self, prs):
        random.seed(42)
        first = prs.parse_sexp("(rand 0 1)")
        random.seed(42)
        assert prs.parse_sexp("(rand 0 1)") == first


class TestGroup:
    def test_inline_members(self, prs):
        g = prs.parse_sexp("(group 'g' [(circle 'a') (circle 'b')])")
        assert isinstance(g, Group)
        assert g.name == "g"
        assert [m.name for m in g.members] == ["a", "b"]

    def test_members_by_name_stay_strings_until_resolved(self, prs):
        g = prs.parse_sexp("(group 'g' ['a' 'b'])")
        assert g.members == ["a", "b"]

    def test_nested_group(self, prs):
        g = prs.parse_sexp("(group 'outer' [(group 'inner' [(circle 'a')])])")
        assert g.members[0].name == "inner"
        assert g.members[0].members[0].name == "a"


class TestCanvas:
    def test_members(self, prs):
        c = prs.parse_sexp("(canvas 'cnv' [(circle 'a')])")
        assert isinstance(c, Canvas)
        assert c.name == "cnv"
        assert [m.name for m in c.members] == ["a"]

    def test_default_bounds(self, prs):
        c = prs.parse_sexp("(canvas 'cnv' [])")
        assert (c.xmin, c.xmax, c.ymin, c.ymax) == (-10, 10, -10, 10)


class TestRepeat:
    def test_count_and_names(self, prs):
        res = prs.parse_sexp("(repeat i 3 (circle f'c{i}' (x i)))")
        assert [c.name for c in res] == ["c0", "c1", "c2"]
        assert [c.x for c in res] == [0, 1, 2]

    def test_several_body_sexps_are_interleaved(self, prs):
        res = prs.parse_sexp("(repeat i 2 (circle f'c{i}') (text f't{i}' 'x'))")
        assert [o.name for o in res] == ["c0", "t0", "c1", "t1"]

    def test_zero_times(self, prs):
        assert prs.parse_sexp("(repeat i 0 (circle f'c{i}'))") == []

    def test_loop_var_is_unbound_after(self, prs):
        prs.parse_sexp("(repeat i 2 (circle f'c{i}'))")
        assert "i" not in prs.boundvars

    def test_nested_repeat(self, prs):
        res = prs.parse_sexp(
            "(group 'g' (repeat i 2 (group f'row{i}'"
            " (repeat j 2 (circle f'c{i}{j}' (x j) (y i))))))"
        )
        assert [row.name for row in res.members] == ["row0", "row1"]
        assert [c.name for c in res.members[1].members] == ["c10", "c11"]
        assert [(c.x, c.y) for c in res.members[1].members] == [(0, 1), (1, 1)]


class TestParse:
    def test_toplevel_objects_and_views_are_separated(self):
        scn = Parser("(circle 'a') (real 'b' 1) (canvas 'cnv' ['a'])").parse()
        assert [o.name for o in scn.objects] == ["a", "b"]
        assert [v.name for v in scn.views] == ["cnv"]

    def test_multiline_source(self):
        src = """
        (circle 'a'
          (r 2)
          (x 1))
        """
        scn = Parser(src).parse()
        assert (scn["a"].r, scn["a"].x) == (2, 1)

    def test_unknown_form_raises(self):
        with pytest.raises(AttributeError):
            Parser("(square 'sq')").parse()
