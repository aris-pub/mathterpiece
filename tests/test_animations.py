import pytest

from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Animation, AtOnce, InOrder, Pair, WaitStep
from mathterpiece.parse import parse

SCENE = (
    "(scene 's' (circle 'c' (pos [0 0])) (text 'label' 'a')"
    " (group 'dots' (circle _ (r 1)) (circle _ (r 2))))"
)


def compile(src):
    return compile_model(parse(f"(real 'k' 1) (bool 'b') {SCENE} {src}"))


def anim(src, name="a"):
    found = compile(src)[name]
    assert isinstance(found, Animation)
    return found


def error(src, match):
    with pytest.raises(CompileError, match=match):
        compile(src)


class TestPairs:
    def test_a_target_and_a_transition(self):
        a = anim("(animation 'a' (k (transition (to 3) (duration 1))))")
        assert isinstance(a.body, Pair)
        assert [(o.name, attr) for o, attr in a.body.targets] == [("k", "value")]
        assert a.body.kind == "number"

    @pytest.mark.parametrize(
        "target, end, kind",
        [
            ("c.pos", "[1 2]", "point"),
            ("c.fill", "'red'", "color"),
            ("label.value", "'b'", "text"),
            ("b", "true", "bool"),
        ],
    )
    def test_the_kind_of_value_comes_from_the_target(self, target, end, kind):
        assert anim(f"(animation 'a' ({target} (transition (to {end}))))").body.kind == kind

    def test_a_stored_transition(self):
        a = anim("(const 'slow' (transition (to 3) (duration 3))) (animation 'a' (k slow))")
        assert isinstance(a.body, Pair)

    def test_ends_that_read_the_scene(self):
        assert anim("(animation 'a' (k (transition (to (* 2 c.x)))))") is not None

    def test_a_group_attribute_is_a_write_to_every_member(self):
        a = anim("(animation 'a' (dots.r (transition (to 3))))")
        assert len(a.body.targets) == 2


class TestComposed:
    def test_at_once(self):
        a = anim(
            "(animation 'a' (at-once (default-duration 2)"
            " (k (transition (to 3))) (c.fill (transition (to 'red')))))"
        )
        assert isinstance(a.body, AtOnce) and len(a.body.parts) == 2
        assert a.body.default_duration == 2.0

    def test_in_order_with_waits_and_names(self):
        a = anim(
            "(animation 'up' (k (transition (to 3) (duration 1))))"
            " (animation 'a' (in-order up (wait 1) (c.pos (transition (to [1 0]) (duration 1)))))"
        )
        assert isinstance(a.body, InOrder)
        first, pause, _ = a.body.parts
        assert isinstance(first, Animation) and first.name == "up"
        assert pause == WaitStep(1.0)


class TestErrors:
    @pytest.mark.parametrize(
        "src, match",
        [
            ("(animation 'a')", "animation takes a name and one animation"),
            (
                "(animation 'a' (k (transition (to 3))) (k (transition (to 4))))",
                "takes a name and one",
            ),
            ("(animation 'a' (k (transition (duration 1))))", "needs an end"),
            (
                "(animation 'a' (k (transition (to 'red'))))",
                "k is a real, but this transition moves a str",
            ),
            (
                "(animation 'a' (c.r (transition (to [1 2]))))",
                "c.r is a real, but this transition moves a list2",
            ),
            ("(animation 'a' (nope (transition (to 1))))", "nope"),
            ("(real 'j' k) (animation 'a' (j (transition (to 1))))", "computed"),
            (
                "(animation 'a' (at-once (k (transition (to 1))) (k (transition (to 2)))))",
                "k is moved twice at once",
            ),
            ("(animation 'a' (at-once (transition (to 1))))", "at-once holds animations"),
            ("(animation 'a' (in-order 3))", "in-order holds animations"),
            ("(animation 'a' (c.fill (transition (to 'reddish'))))", "'reddish' is not a color"),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)


class TestExport:
    def test_writes_animations(self):
        doc = to_json(
            compile(
                "(const 'slow' (transition (to 3) (duration 3) (ease 'ease-in')))"
                " (animation 'up' (k slow))"
                " (animation 'a' (in-order (default-duration 1) up (wait 0.5)"
                " (at-once (c.pos (transition (to [1 2])))"
                " (c.fill (transition (to 'red') (ease (step 1)))))"
                " (dots.r (transition (from 0) (to (* 2 k))))))"
            )
        )
        names, objs = doc["names"], doc["objects"]
        k, c = names["k"], names["c"]
        up = objs[names["up"]]
        assert up["kind"] == "animation"
        assert up["body"] == [
            "pair",
            [[k, "value"]],
            "number",
            ["transition", {"to": 3.0, "duration": 3.0, "ease": "ease-in"}],
        ]
        body = objs[names["a"]]["body"]
        assert body[:2] == ["in-order", {"default-duration": 1.0}]
        assert body[2] == ["animation", names["up"]]
        assert body[3] == ["wait", 0.5]
        assert body[4] == [
            "at-once",
            {},
            ["pair", [[c, "pos"]], "point", ["transition", {"to": [1.0, 2.0]}]],
            [
                "pair",
                [[c, "fill"]],
                "color",
                ["transition", {"to": "#ff0000ff", "ease": ["step", 1.0]}],
            ],
        ]
        targets, kind, transition = body[5][1:]
        assert len(targets) == 2 and kind == "number"
        assert transition == ["transition", {"from": 0.0, "to": ["*", 2.0, ["read", k, "value"]]}]


def test_a_motif_parameter_an_animation_writes_stays_reactive():
    from mathterpiece.model import Bound, Motif, local_names

    m = compile_model(
        parse(
            "(motif 'dot' (params (r 1.0)) (circle 'c' (r r))) (scene 's' (dot 'd'))"
            " (animation 'a' (in-order (d.r (transition (to 2) (duration 1)))))"
        )
    )
    d = m["d"]
    assert isinstance(d, Motif)
    assert isinstance(local_names(d)["c"].r, Bound)  # ty: ignore[unresolved-attribute]


def test_a_fill_may_move_to_none():
    a = compile("(animation 'a' (c.fill (transition (to 'none'))))")["a"]
    assert a.body.transition.to == "none"


def test_an_int_target_moves_in_whole_numbers():
    m = compile_model(
        parse(
            "(motif 'm' (params (n 3)) (circle 'c')) (scene 's' (m 'd'))"
            " (animation 'a' (d.n (transition (to 9))))"
        )
    )
    assert m["a"].body.kind == "int"  # ty: ignore[unresolved-attribute]


class TestStoredWaits:
    # A wait is the transition that changes nothing, so it may stand where an animation is
    # expected, written in place or stored in a const.
    def test_a_const_holding_a_wait(self):
        src = (
            "(real 'k' 0) (const 'pause' (wait 1.5)) (scene _)"
            " (animation 'a' (in-order (k (transition (to 1) (duration 1))) pause))"
        )
        body = compile_model(parse(src))["a"].body  # ty: ignore[unresolved-attribute]
        assert isinstance(body, InOrder)
        assert body.parts[1] == WaitStep(1.5)

    def test_a_const_holding_an_in_order_of_waits(self):
        src = (
            "(real 'k' 0) (const 'pause' (in-order (wait 1) (wait 0.5))) (scene _)"
            " (animation 'a' (in-order (k (transition (to 1) (duration 1))) pause))"
        )
        body = compile_model(parse(src))["a"].body  # ty: ignore[unresolved-attribute]
        assert body.parts[1] == InOrder(parts=(WaitStep(1.0), WaitStep(0.5)))

    def test_a_transition_with_no_ends_does_not(self):
        src = (
            "(real 'k' 0) (const 'still' (transition (duration 1))) (scene _)"
            " (animation 'a' (in-order (k (transition (to 1) (duration 1))) still))"
        )
        with pytest.raises(CompileError, match="holds animations"):
            compile_model(parse(src))

    def test_the_error_names_every_kind_of_part(self):
        src = "(real 'k' 0) (scene _) (animation 'a' (in-order (k (transition (to 1))) 3))"
        with pytest.raises(CompileError, match="at-once, in-order, wait, or another animation"):
            compile_model(parse(src))


class TestGroupTargets:
    # A group's attribute as a target is written to each member, as that member's would be.
    @pytest.mark.parametrize(
        "target, value, attr",
        [("dots.k", "1", "k"), ("circles.pos", "[1 1]", "pos")],
    )
    def test_each_member(self, target, value, attr):
        src = (
            "(motif 'dot' (params (k 0.0)) (circle 'c' (r k)))"
            " (scene 's' (group 'dots' (dot _) (dot _)) (group 'circles' (circle _) (circle _)))"
            f" (button 'b' (animation ({target} (transition (to {value}) (duration 0)))))"
        )
        doc = to_json(compile_model(parse(src)))
        anim = doc["objects"][doc["objects"][doc["names"]["b"]]["animation"]]
        assert [t[1] for t in anim["body"][1]] == [attr, attr]

    def test_what_reads_the_members_values_follows_them(self):
        # The members' parameter is written, so a shape reading it must not be folded.
        src = (
            "(motif 'dot' (params (k 0.0)) (circle 'c' (r k)))"
            " (scene 's' (group 'dots' (dot _) (dot 'named')))"
            " (button 'b' (animation (dots.k (transition (to 3) (duration 0)))))"
        )
        doc = to_json(compile_model(parse(src)))
        radii = [o["attrs"]["r"] for o in doc["objects"] if o["kind"] == "circle"]
        assert all(isinstance(r, list) for r in radii)

    def test_a_member_that_computes_it(self):
        src = (
            "(real 'k' 1) (scene 's' (group 'g' (circle _) (circle _ (r k))))"
            " (button 'b' (animation (g.r (transition (to 1) (duration 0)))))"
        )
        with pytest.raises(CompileError, match="a member of 'g' computes its r"):
            compile_model(parse(src))
