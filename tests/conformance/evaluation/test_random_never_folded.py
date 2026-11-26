"""Conformance tests of the rule random-never-folded (docs/spec/evaluation.md)."""

from ._shared import RAND, is_bound, pytest, rule


@rule("random-never-folded")
class TestRandomNeverFolded:
    @pytest.mark.parametrize(
        "src",
        [
            RAND + "(rand-seed s 1) (real v (rand))",
            RAND + "(rand-seed s 1) (int v (rand-int 1 6))",
            RAND + "(rand-seed s 1) (real|none v (pick (as list[real] {1 2})))",
            RAND + "(rand-seed s 1) (list[int] v (shuffle {1 2 3}))",
        ],
    )
    def test_a_random_value_is_known_only_while_drawing(self, src):
        assert is_bound(src, "v")
