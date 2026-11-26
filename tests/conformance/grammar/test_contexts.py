"""Conformance tests of the rule contexts (docs/spec/grammar.md)."""

from ._shared import REJECTION, accepted, in_folder, pytest, rejected, rule


@rule("contexts")
class TestContexts:
    @pytest.mark.parametrize(
        "src",
        [
            "(circle c (r 1))",
            "(scene s (circle c (r 1))) (on-click c)",
            "(formula f $'\\term{a}{x}') (term a (fill #'red'))",
            "(scene s (group g (real k 1) (circle c (r 1))))",
            "(scene s (motif m () (circle_ (r 1))))",
            "(scene s (circle c (r 1)) (canvas v s))",
            "(namespace n (func f ((real x)) x))",
            "(palette p (palette q ('a' #'red')))",
            "(variant v ((real k 1 (>= 0))) (circle (r k)) (circle (r k)))",
            "(func f ((real x)) x x)",
            "(scene s (group g (clip (line (from [0 0]) (to [1 1]))) (circle c (r 1))))",
            "(real k 0) (scene s (circle c (r 1))) (canvas v s (move k (to 1)))",
            "(real k 0) (motif m () (animation a (move k (to 1) (duration 1))) (circle_ (r 1)))",
        ],
    )
    def test_an_item_that_the_body_does_not_hold_is_an_error(self, src):
        rejected(src)

    def test_a_file_to_import_holds_only_what_it_may(self, tmp_path):
        with pytest.raises(REJECTION):
            in_folder(tmp_path, {"lib.mtp": "(real k 1)\n"}, "(import lib)\n(real v lib.k)\n")

    @pytest.mark.parametrize(
        "src",
        [
            "(scene s (real k 1 (>= 0)) (circle c (r k)))",
            "(scene s (group g (circle c (r 1)) (circle|none d (r 1)) (exists-when d true)))",
            "(motif m ((real k 1 (>= 0))) (circle_ (r k))) (scene s (m a))",
            "(namespace n (real k 1) (namespace m (real j 2)))",
            "(palette p (a #'red') (b #'blue'))",
            "(formula f $'\\term{a}{x}' (term a (fill #'red')))",
        ],
    )
    def test_items_that_the_body_holds(self, src):
        accepted(src)
