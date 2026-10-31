import pytest
from helpers import with_scene

from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Bound, Drag, State, local_names
from mathterpiece.parse import parse


def scene(src):
    return compile_model(with_scene(src))


def error(src, match=None):
    with pytest.raises(CompileError, match=match):
        scene(src)


def drag(model) -> Drag:
    (found,) = model.listeners
    return found


PIN = "(motif 'pin' (params) (circle 'head' (r 0.2)) (line 'stem' (from [0 0]) (to [0 -1])))"


class TestOnDrag:
    def test_drags_a_shape(self):
        m = scene("(circle 'u' (pos [0 1])) (on-drag u u.pos)")
        d = drag(m)
        assert d.node is m["u"]
        assert d.conditions == ()
        assert d.when is None
        assert d.name is None

    def test_drags_a_motif(self):
        m = scene(f"{PIN} (pin 'p') (on-drag p p.pos)")
        assert drag(m).node is m["p"]

    def test_drags_a_member_by_path(self):
        m = scene(f"{PIN} (pin 'p') (on-drag p.head p.head.pos)")
        assert drag(m).node is local_names(m["p"])["head"]

    @pytest.mark.parametrize("target", ["x", "y", "pos"])
    def test_target(self, target):
        assert drag(scene(f"(circle 'u') (on-drag u u.{target})")).target == target

    def test_moves_one_coordinate_while_the_other_is_computed(self):
        m = scene("(circle 'bar') (circle 'h' (x 0) (y bar.y)) (on-drag h h.x (>= h.x 0))")
        assert drag(m).target == "x"

    def test_a_number_the_position_depends_on(self):
        m = scene("(real 'theta' 40) (circle 'p' (pos (polar 6 theta))) (on-drag p theta)")
        d = drag(m)
        assert (d.node, d.target_obj, d.target) == (m["p"], m["theta"], "value")

    def test_a_motif_parameter(self):
        m = scene(
            "(motif 'arm' (params (angle 0.0)) (circle 'tip' (pos (polar 3 angle))))"
            " (arm 'a') (on-drag a.tip a.angle)"
        )
        assert drag(m).target == "angle"

    def test_conditions(self):
        m = scene(
            "(circle 'c') (circle 'u' (pos [0 1])) (on-drag u u.pos (<= (dist u c) 3) (>= u.y 0))"
        )
        assert len(drag(m).conditions) == 2

    def test_when_a_condition(self):
        m = scene("(real 'k' 1) (circle 'u') (on-drag u u.pos (when (> k 0)))")
        assert drag(m).when is not None

    def test_when_a_state(self):
        m = scene("(real 'k' 1) (state 'on' (= k 1)) (circle 'u') (on-drag u u.pos (when on))")
        assert isinstance(drag(m).when, State)

    def test_position_stays_reactive(self):
        m = scene("(circle 'u' (pos [0 1])) (circle 'f' (x u.x)) (on-drag u u.pos)")
        assert isinstance(m["f"].x, Bound)

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(on-drag)", "on-drag needs"),
            ("(circle 'u') (on-drag u)", "on-drag needs"),
            ("(circle 'u') (on-drag nope nope.pos)", "nope"),
            ("(real 'k') (on-drag k k.value)", "cannot be dragged"),
            ("(circle 'c') (circle 'u' (x c.x)) (on-drag u u.pos)", "computed"),
            ("(circle 'c') (circle 'u' (x c.x)) (on-drag u u.x)", "computed"),
            ("(circle 'c') (circle 'u') (on-drag u c.pos)", "u.x, u.y, u.pos, or a number"),
            ("(circle 'u') (on-drag u u.fill)", "u.x, u.y, u.pos, or a number"),
            ("(circle 'u') (on-drag u u.pos 3)", "true or false"),
            ("(circle 'u') (on-drag u u.pos (when 3))", "true or false"),
            ("(circle 'u') (on-drag u u.pos (when (> 1 0)) (when (> 1 0)))", "twice"),
            ("(circle 'u') (on-drag u u.pos (r 3))", "unexpected"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestExport:
    def test_writes_the_listener(self):
        doc = to_json(
            scene(
                "(real 'k' 1) (state 'on' (= k 1)) (circle 'u')"
                " (on-drag u u.pos (> u.x 0) (when on))"
            )
        )
        (d,) = [o for o in doc["objects"] if o["kind"] == "on-drag"]
        u, on = doc["names"]["u"], doc["names"]["on"]
        assert d["target"] == [u, "pos"]
        assert d["conditions"] == [[">", ["read", u, "x", None], 0.0]]
        assert d["when"] == ["holds", on]

    def test_no_when(self):
        doc = to_json(scene("(circle 'u') (on-drag u u.pos)"))
        (d,) = [o for o in doc["objects"] if o["kind"] == "on-drag"]
        assert d["when"] is None


def test_export_a_number_target():
    doc = to_json(scene("(real 'theta' 40) (circle 'p' (pos (polar 6 theta))) (on-drag p theta)"))
    (d,) = [o for o in doc["objects"] if o["kind"] == "on-drag"]
    assert d["node"] == doc["names"]["p"]
    assert d["target"] == [doc["names"]["theta"], "value"]
    assert d["type"] == "real"


class TestReadingControls:
    # Listeners are controls, and controls read each other: on-drag as on-click does.
    def test_when_reads_a_toggle(self):
        src = "(scene 's' (circle 'a')) (toggle 'show' self) (on-drag a a.pos (when show))"
        assert compile_model(parse(src))

    def test_on_click_does_the_same(self):
        src = (
            "(real 'k' 0) (scene 's' (circle 'a')) (toggle 'show' self)"
            " (on-click a (animation (k (transition (to 1) (duration 0)))) (when show))"
        )
        assert compile_model(parse(src))


class TestDragTargetsMoveTheNode:
    # A drag's target is the node's own position, or a number its position depends on.
    @pytest.mark.parametrize(
        "src",
        [
            "(scene 's' (circle 'a')) (on-drag a a.r)",
            "(real 'k' 1) (scene 's' (circle 'a' (r k))) (on-drag a k)",
            "(scene 's' (circle 'a') (circle 'd')) (on-drag a d.x)",
        ],
    )
    def test_rejected(self, src):
        with pytest.raises(CompileError, match="does not move when"):
            compile_model(parse(src))

    def test_the_error_points_at_the_target(self):
        with pytest.raises(CompileError, match="^1:37: a does not move when a.r changes"):
            compile_model(parse("(scene 's' (circle 'a')) (on-drag a a.r)"))

    @pytest.mark.parametrize(
        "src",
        [
            "(real 'k' 1) (scene 's' (circle 'q' (pos (polar 1 k))) (circle 'a' (pos q.pos)))"
            " (on-drag a k)",
            "(real 'k' 1) (scene 's' (group 'g' (transform (rotate k)) (circle 'a' (pos [1 0]))))"
            " (on-drag a k)",
            "(real 'k' 1) (motif 'm' (params (t 0.0)) (circle 'tip' (pos (polar 1 t))))"
            " (scene 's' (m 'i' (t k))) (on-drag i.tip k)",
            "(real 'k' 1) (scene 's' (circle 'a' (pos (let ((h (* 2 k))) [h 0])))) (on-drag a k)",
            "(real 'k' 1) (scene 's' (circle 'a' (r k) (x (let ((h (* 2 self.r))) h))))"
            " (on-drag a k)",
        ],
    )
    def test_accepted_through_other_objects(self, src):
        assert compile_model(parse(src))


class TestDraggingAGroup:
    # Dragging a group moves each member's position by the same amount.
    @pytest.mark.parametrize("target", ["pos", "x", "y"])
    def test_accepted(self, target):
        m = compile_model(
            parse(
                f"(scene 's' (group 'g' (circle _) (circle _ (pos [2 0])))) (on-drag g g.{target})"
            )
        )
        d = drag(m)
        assert (d.node, d.target_obj, d.target) == (m["g"], m["g"], target)

    def test_written_as_a_drag_of_the_groups_position(self):
        doc = to_json(compile_model(parse("(scene 's' (group 'g' (circle _))) (on-drag g g.pos)")))
        (d,) = [o for o in doc["objects"] if o["kind"] == "on-drag"]
        assert d["target"] == [doc["names"]["g"], "pos"]

    def test_a_member_whose_position_is_computed(self):
        src = "(real 'k' 0) (scene 's' (group 'g' (circle _) (circle _ (x k)))) (on-drag g g.pos)"
        with pytest.raises(CompileError, match="a member of 'g' computes its"):
            compile_model(parse(src))

    def test_only_the_groups_own_position(self):
        src = "(real 'k' 0) (scene 's' (group 'g' (circle _ (r k)))) (on-drag g k)"
        with pytest.raises(CompileError, match="a group is dragged by its own pos, x or y"):
            compile_model(parse(src))
