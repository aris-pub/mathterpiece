"""Conformance tests of the rule declare-before-use (docs/spec/scope.md)."""

from ._shared import accepted, compile_error, rule


@rule("declare-before-use")
class TestDeclareBeforeUse:
    def test_a_canvas_comes_after_the_scene_in_its_body(self):
        compile_error("(canvas cv s) (scene s (circle c (r 1)))")
        accepted("(scene s (circle c (r 1))) (canvas cv s)")

    def test_an_exists_when_comes_after_its_shape(self):
        compile_error("(scene s (exists-when c true) (circle|none c (r 1)))")
        accepted("(scene s (circle|none c (r 1)) (exists-when c true))")
