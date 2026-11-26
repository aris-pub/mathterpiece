"""Conformance tests of the rule docstrings (docs/spec/grammar.md)."""

from ._shared import ANIMATION, accepted, compile_error, mtpc, obj, pytest, rejected, rule


@rule("docstrings")
class TestDocstrings:
    @pytest.mark.parametrize(
        "src",
        [
            "(real k 1 doc@'d' (>= 0))",
            "(func f ((real x)) doc@'d' (* 2 x))",
            "(scene s (circle c (r 1) doc@'d'))",
            "(scene s (circle c (r 1))) (canvas v s (on-click c doc@'d'))",
            f"(real k 0) (button b {ANIMATION} doc@'d')",
            f"(real k 0) (play p {ANIMATION} doc@'d')",
            f"(real k 0) (scene s (circle c (r 1))) (canvas v s (on-click c {ANIMATION} doc@'d'))",
            f"(real k 0) (scene s (circle c (r 1))) (canvas v s (on-ready {ANIMATION} doc@'d'))",
            "(motif m ((real k 1 (>= 0))) doc@'d' (circle_ (r k)))",
            "(scene s (group g (defaults (fill #'red')) doc@'d' (circle c (r 1))))",
            "(formula f $'x' doc@'d')",
            "(formula f $'\\term{a}{x}' (defaults (padding 3)) doc@'d' (term a (fill #'red')))",
            "(scene s (circle c (r 1))) (canvas v (x 0) (y 0) (width 1) (height 1) doc@'d' s)",
        ],
    )
    def test_after_the_arguments_and_before_the_body(self, src):
        accepted(src)

    @pytest.mark.parametrize(
        "src",
        [
            "(real k 1 (>= 0) doc@'d')",
            "(func f ((real x)) (* 2 x) doc@'d')",
            "(scene s (circle c doc@'d' (r 1)))",
            f"(real k 0) (button b doc@'d' {ANIMATION})",
            f"(real k 0) (play p doc@'d' {ANIMATION})",
            f"(real k 0) (scene s (circle c (r 1))) (canvas v s (on-click c doc@'d' {ANIMATION}))",
            f"(real k 0) (scene s (circle c (r 1))) (canvas v s (on-ready doc@'d' {ANIMATION}))",
            "(motif m () (circle_ (r 1)) doc@'d')",
            "(scene s (group g (circle c (r 1)) doc@'d'))",
            "(scene s (group g doc@'d' (defaults (fill #'red')) (circle c (r 1))))",
            "(formula f doc@'d' $'x')",
            "(formula f $'\\term{a}{x}' doc@'d' (defaults (padding 3)) (term a (fill #'red')))",
            "(formula f $'\\term{a}{x}' (term a (fill #'red')) doc@'d')",
            "(scene s (circle c (r 1))) (canvas v (x 0) (y 0) doc@'d' (width 1) (height 1) s)",
            "(scene s (circle c (r 1))) (canvas v s doc@'d')",
        ],
    )
    def test_in_any_other_place_it_is_an_error(self, src):
        compile_error(src)

    def test_at_most_one(self):
        compile_error("(real k 1 doc@'a' doc@'b')")

    def test_an_interpolated_docstring_is_an_error(self):
        rejected("(real k 1 (doc f'd{k}'))")

    @pytest.mark.parametrize(
        "src",
        [
            "(motif m () (real k 1 doc@'d' (const)) (circle c (r k)))",
            "(motif m ((real r 1 (>= 0))) (real d (* 2 r) doc@'d') (circle c (r d)))",
        ],
    )
    def test_a_variable_in_a_motif_body_may_have_one(self, src):
        accepted(src)

    def test_a_variable_in_a_motif_body_keeps_its_docstring(self):
        d = mtpc(
            "(motif m ((real r 1 (>= 0))) (real d (* 2 r) doc@'twice r') (circle c (r d)))"
            " (scene s (m a) (m b (r 2)))"
        )
        assert obj(d, "a")["attrs"]["d"]["doc"] == "twice r"
        assert obj(d, "b")["attrs"]["d"]["doc"] == "twice r"
        assert "doc" not in obj(d, "a")["attrs"]["r"]

    def test_a_docstring_after_a_motif_body_variable_constraint_is_an_error(self):
        compile_error("(motif m () (real k 1 (const) doc@'d') (circle c (r k)))")

    def test_the_docstring_is_kept(self):
        assert obj(mtpc("(real k 1 doc@'the radius')"), "k")["doc"] == "the radius"
