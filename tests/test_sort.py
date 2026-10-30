import random

import pytest

from mathterpiece.backends.mpl import Evaluator
from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Free
from mathterpiece.parse import parse

POINTS = (
    "(scene 's' (circle 'x' (pos [0 0]))"
    " (group 'points' (circle _ (pos [6 8]) (r 1)) (circle _ (pos [1 0]) (r 2))"
    " (circle _ (pos [3 4]) (r 3))))"
)
DISTANCES = "(map points p (dist x p))"  # 10, 1, 5


def evaluate(src):
    m = compile_model(parse(f"{POINTS} (real 'v' {src})"))
    ev = Evaluator(m, random.Random(0))
    return m, ev, ev.value(m["v"], "value")


def value(src):
    return evaluate(src)[2]


def folded(src):
    m = compile_model(parse(f"(real 'v' {src}) (scene _)"))
    return m["v"].value  # ty: ignore[unresolved-attribute]


class TestNumbers:
    @pytest.mark.parametrize(
        "op, k, expected",
        [
            ("sort", 0, 1),
            ("sort", 2, 10),
            ("sort-asc", 1, 5),
            ("sort-desc", 0, 10),
            ("sort-desc", 2, 1),
            ("reverse", 0, 5),
            ("reverse", 2, 10),
        ],
    )
    def test_while_drawing(self, op, k, expected):
        assert value(f"(let ((ds ({op} {DISTANCES}))) ds[{k}])") == pytest.approx(expected)

    @pytest.mark.parametrize(
        "src, expected",
        [
            ("(let ((d (sort [3 1 2]))) d[0])", 1.0),
            ("(let ((d (sort-desc [3 1 2]))) d[0])", 3.0),
            ("(let ((d (reverse [3 1 2]))) d[0])", 2.0),
            ("(let ((d (sort (reverse [3 1 2])))) d[2])", 3.0),
        ],
    )
    def test_known_lists_fold(self, src, expected):
        assert folded(src) == Free(expected)

    def test_follows_the_scene(self):
        m, ev, _ = evaluate(f"(let ((ds (sort {DISTANCES}))) ds[0])")
        ev.write(m["points"].members[0], "x", 0.0)
        ev.write(m["points"].members[0], "y", 0.5)
        assert ev.value(m["v"], "value") == pytest.approx(0.5)


class TestByKey:
    def test_members_ordered_by_their_key(self):
        assert value("(let ((ns (sort points p (dist x p)))) ns[0].x)") == 1
        assert value("(let ((ns (sort points p (dist x p)))) ns[2].r)") == 1

    def test_descending(self):
        assert value("(let ((ns (sort-desc points p p.r))) ns[0].r)") == 3

    def test_members_work_as_points(self):
        assert value("(let ((ns (sort points p (dist x p)))) (dist x ns[1]))") == pytest.approx(5)

    def test_reverse_a_list_of_members(self):
        assert value("(let ((ns (reverse (sort-asc points p p.r)))) ns[0].r)") == 3

    def test_map_over_a_list_of_members(self):
        src = "(let ((ns (sort points p (dist x p))) (rs (map ns n n.r))) rs[1])"
        assert value(src) == 3

    def test_follows_the_scene(self):
        m, ev, _ = evaluate("(let ((ns (sort points p p.r))) ns[0].x)")
        ev.write(m["points"].members[2], "r", 0.5)
        assert ev.value(m["v"], "value") == 3

    def test_an_authors_own_sort_hides_the_librarys(self):
        m = compile_model(
            parse("(func 'sort' (params (a 0.0)) (* a 2)) (real 'v' (sort 4)) (scene _)")
        )
        assert m["v"].value == Free(8.0)  # ty: ignore[unresolved-attribute]


class TestExport:
    def test_reading_a_sorted_member_depends_on_every_member(self):
        doc = to_json(
            compile_model(parse(f"{POINTS} (real 'v' (let ((ns (sort points p p.x))) ns[0].r))"))
        )
        v = doc["names"]["v"]
        for m in doc["objects"][doc["names"]["points"]]["members"]:
            assert f"{v}.value" in doc["depends"][f"{m}.r"]
            assert f"{v}.value" in doc["depends"][f"{m}.x"]


class TestErrors:
    @pytest.mark.parametrize(
        "src, match",
        [
            ("(sort 3)", "sorts a list of numbers"),
            ("(reverse 3)", "reverses a list"),
            ("(sort points)", "sorts a list of numbers"),
            ("(sort [1 2] p p)", "or the members of a group by a key"),
            ("(let ((ns (sort points p 'a'))) 0)", "the key of a sort must be a number"),
            ("(let ((ns (sort points p p.r))) ns[5].r)", "has no part"),
            ("(let ((ns (sort points p p.r))) ns[0].nope)", "has no attribute 'nope'"),
            ("(sort points p p.r)", "expected real"),
        ],
    )
    def test_invalid(self, src, match):
        with pytest.raises(CompileError, match=match):
            compile_model(parse(f"{POINTS} (real 'v' {src})"))

    def test_mixed_groups(self):
        src = "(scene 's' (group 'g' (circle _) (rect _))) (real 'v' (let ((ns (sort g p p.x))) 0))"
        with pytest.raises(CompileError, match="must all be the same kind of shape"):
            compile_model(parse(src))
