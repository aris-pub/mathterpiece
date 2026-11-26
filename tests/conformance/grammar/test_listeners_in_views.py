"""Conformance tests of the rule listeners-in-views (docs/spec/grammar.md)."""

from ._shared import accepted, compile_error, mtpc, rule


@rule("listeners-in-views")
class TestListenersInViews:
    def test_a_listener_at_the_top_level_is_an_error(self):
        compile_error("(scene s (circle c (r 1))) (on-click c)")

    def test_a_listener_is_heard_in_its_own_view(self):
        d = mtpc("(scene s (circle c (r 1))) (canvas v s (on-click c)) (canvas w s)")
        listener = next(o for o in d["objects"] if o["kind"] == "on-click")
        assert listener["in"] == [d["names"]["v"]]

    def test_a_listener_on_its_own_view_leaves_out_its_name(self):
        accepted(
            "(real k 0) (scene s) (canvas v s (on-view (animation (move k (to 1) (duration 1)))))"
        )

    def test_a_listener_has_no_in(self):
        compile_error("(scene s (circle c (r 1))) (canvas v s (on-click c (in v)))")
