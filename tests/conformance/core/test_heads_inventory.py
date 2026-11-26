"""Tests of the defaults given in the rows of the inventory of heads (docs/spec/heads.md), which has
no rules of its own."""

from ._shared import POINTER_EVENTS, RANGE, compile_error, pytest, same_meaning


class TestInventory:
    # The heads of "Inventory of heads" that have a default given in their row.
    @RANGE
    def test_range_has_a_gap_of_1_by_default(self):
        same_meaning(
            "(int n 3 (>= 0) (<= 5)) (list[int] v (range 0 n))",
            "(int n 3 (>= 0) (<= 5)) (list[int] v (range 0 n (gap 1)))",
        )

    @RANGE
    def test_range_of_one_argument_is_an_error(self):
        compile_error("(list[int] v (range 3))")

    @POINTER_EVENTS
    @pytest.mark.parametrize("head", ["group", "row", "column"])
    def test_pointer_events_on_a_container_is_an_error(self, head):
        compile_error(f"(scene s ({head} g (pointer-events false) (circle c (r 1))))")

    def test_dash_has_an_offset_of_0_by_default(self):
        same_meaning(
            "(scene s (line l (to [1 1]) (dash {4 2})))",
            "(scene s (line l (to [1 1]) (dash {4 2} 0)))",
        )
