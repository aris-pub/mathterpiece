"""Conformance tests of the rule like-copies (docs/spec/core.md)."""

from ._shared import compile_error, rule, same_meaning


@rule("like-copies")
class TestLikeCopies:
    def test_like_on_a_shape(self):
        same_meaning(
            "(scene s (circle a (r 2) (fill #'red')) (circle b (like a) (fill #'blue')))",
            "(scene s (circle a (r 2) (fill #'red')) (circle b (fill #'blue') (r 2)))",
        )

    def test_like_copies_what_the_items_read(self):
        src = "(real k 1 (>= 0)) (scene s (circle a (r (* 2 k))) (circle b (like a)))"
        same_meaning(
            src, "(real k 1 (>= 0)) (scene s (circle a (r (* 2 k))) (circle b (r (* 2 k))))"
        )

    def test_like_splits_pos(self):
        same_meaning(
            "(scene s (circle a (pos [1 2]) (r 1)) (circle b (like a) (x 5)))",
            "(scene s (circle a (pos [1 2]) (r 1)) (circle b (x 5) (y (. {1 2} 1)) (r 1)))",
        )

    def test_like_on_a_text_copies_its_string(self):
        same_meaning(
            "(scene s (text a 'hi' (halign 'start')) (text b (like a) (x 1)))",
            "(scene s (text a 'hi' (halign 'start')) (text b 'hi' (x 1) (halign 'start')))",
        )

    def test_like_of_a_shape_of_another_kind_is_an_error(self):
        compile_error("(scene s (circle a (r 1)) (rect b (like a)))")

    def test_like_of_a_group_is_an_error(self):
        compile_error("(scene s (group a (circle_ (r 1))) (group b (like a)))")

    def test_like_on_a_font(self):
        same_meaning(
            "(font a (size 12) (weight 700)) (font b (like a) (size 14))",
            "(font a (size 12) (weight 700)) (font b (size 14) (weight 700))",
        )

    def test_like_on_a_term(self):
        same_meaning(
            "(formula f $'\\term{a}{x}\\term{b}{y}' (term a (fill #'red')) (term b (like a)))",
            "(formula f $'\\term{a}{x}\\term{b}{y}' (term a (fill #'red')) (term b (fill #'red')))",
        )

    def test_like_on_a_move(self):
        same_meaning(
            "(real k 0) (transition t k (to 1) (duration 2)) (button b (animation (move k (like t) "
            "(to 3))))",
            "(real k 0) (transition t k (to 1) (duration 2)) (button b (animation (move k (to 3) "
            "(duration 2))))",
        )

    def test_like_on_an_instance_copies_its_defaults(self):
        motif = "(motif m () (circle_ (r 1)))\n"
        same_meaning(
            motif + "(scene s (m a (defaults (pointer-events false))) (m b (like a)))",
            motif
            + "(scene s (m a (defaults (pointer-events false))) "
            + "(m b (defaults (pointer-events false))))",
        )
