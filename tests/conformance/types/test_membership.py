"""Conformance tests of the rule membership (docs/spec/types.md)."""

from ._shared import TYPES_REDESIGN, accepted, rule


@rule("membership")
class TestMembership:
    @TYPES_REDESIGN
    def test_is_narrows_a_union(self):
        accepted("(func size ((point|circle p)) (if (is p circle) p.r 0))")
