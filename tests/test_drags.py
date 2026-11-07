"""A drag writes its target from the pointer (docs/reference.md, "Dragging"; mtp-r6al): a shape's
own position follows the pointer, and any other target takes the value of a move's to, an
expression of the name pointer."""

from helpers import doc, error, model
from mtpc_check import errors

K = "(real k 0 (>= 0) (<= 10))"


def drag(m):
    (d,) = [o for o in m.objects if o.kind == "on-drag"]
    return d


class TestAMove:
    def test_a_number_from_the_pointer(self):
        m = model(f"{K} (scene s (circle c (x k))) (on-drag c (move k (to pointer.x)))")
        d = drag(m)
        assert d.data["target"] == (m.id("k"), None)
        assert d.data["map"].bound

    def test_a_point_from_the_pointer(self):
        m = model("(point p [0 0]) (scene s (circle c (pos p))) (on-drag c (move p (to pointer)))")
        assert drag(m).data["target"] == (m.id("p"), None)

    def test_conditions_still_limit_it(self):
        m = model(f"{K} (scene s (circle c (x k))) (on-drag c (move k (to pointer.x)) (<= k 8))")
        assert drag(m).data["conditions"]

    def test_the_short_form_is_unchanged(self):
        m = model("(scene s (circle c)) (on-drag c c.pos)")
        d = drag(m)
        assert d.data["target"] == (m.id("c"), "pos") and "map" not in d.data

    def test_it_is_written_with_its_map(self):
        d = doc(f"{K} (scene s (circle c (x k))) (on-drag c (move k (to pointer.x)))")
        o = next(o for o in d["objects"] if o["kind"] == "on-drag")
        assert "bound" in o["map"]
        assert errors(d) == []


class TestErrors:
    S = f"{K} (scene s (circle c (x k)))"

    def test_a_number_the_position_depends_on_needs_a_move(self):
        error(f"{self.S} (on-drag c k)", r"\(on-drag c \(move k \(to …\)\)\)")

    def test_a_drag_move_takes_only_to(self):
        for extra in ["(duration 1)", "(ease linear)", "(from 0)"]:
            error(
                f"{self.S} (on-drag c (move k (to pointer.x) {extra}))",
                "a drag's move takes its target and its to, and nothing else",
            )

    def test_it_needs_a_to(self):
        error(f"{self.S} (on-drag c (move k))", "a drag's move takes its target and its to")

    def test_the_to_fits_the_target(self):
        error(f"{self.S} (on-drag c (move k (to pointer)))", "expected real")

    def test_pointer_is_known_only_in_a_drag(self):
        error("(point v pointer)", "unknown name 'pointer'")


class TestNameStrings:
    # mtp-m2rw: a name string stands for the name it builds, a move's target included.
    def test_a_drag_moves_a_variable_named_by_a_string(self):
        m = model(
            "(real k-0 0) (real k-1 0) (scene s (circle c-0 (x k-0)) (circle c-1 (x k-1)))"
            " (foreach i 2 (on-drag #'c-{i}' (move #'k-{i}' (to pointer.x))))"
        )
        targets = [o.data["target"] for o in m.objects if o.kind == "on-drag"]
        assert targets == [(m.id("k-0"), None), (m.id("k-1"), None)]

    def test_an_animation_moves_an_attribute_named_by_a_string(self):
        m = model(
            "(scene s (foreach i 2 (circle #'c-{i}' (r 1))))"
            " (animation a (foreach i 2 (move #'c-{i}'.r (to 2) (duration 1))))"
        )
        steps = m.get("a").data["steps"]
        assert [s[1] for s in steps[1:]] == [(m.id("c-0"), "r"), (m.id("c-1"), "r")]
