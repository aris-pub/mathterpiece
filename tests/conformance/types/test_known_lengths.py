"""Conformance tests of the rule known-lengths (docs/spec/types.md)."""

from ._shared import KNOWN_IF, accepted, compile_error, pytest, rule


@rule("known-lengths")
class TestKnownLengths:
    @pytest.mark.parametrize(
        "src",
        [
            "(real a 1) (real v (. {a 0 1} 1))",
            "(list[real] xs {1 2 3} (length 3)) (real v (. xs 1))",
            "(real a 1) (list[real] xs {a 0 1}) (real v (. xs 1))",
            "(func f ((real a)) {a a}) (real b 1) (real v (. (f b) 1))",
            "(scene s (group g (circle c1 (r 1)) (circle c2 (r 2)))) (real v (. g.r 1))",
            "(real a 1) (list[list[real]] xs {{a 1} {2 a}}) (real v (. (. xs 0) 1))",
        ],
    )
    def test_an_item_of_a_list_of_known_length_is_never_none(self, src):
        accepted(src)

    def test_a_free_list_declared_with_no_length(self):
        compile_error("(list[real] xs {1 2 3}) (real v (. xs 1))")

    @KNOWN_IF
    def test_an_if_whose_branches_have_the_same_known_length(self):
        accepted("(bool c true) (real a 1) (real v (. (if c {a 1} {2 a}) 1))")
