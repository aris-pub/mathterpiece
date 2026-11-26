"""Conformance tests of the rule none-propagates (docs/spec/evaluation.md)."""

from ._shared import INVERSE, NONE_ARGUMENT, NONE_COLLECTION, REVERSE, rule, value


@rule("none-propagates")
class TestNonePropagates:
    def test_an_operation_on_none_gives_none(self):
        assert value("(func f ((real|none x)) (+ x 1)) (real|none v (f none))", "v") is None

    def test_or_default_gives_a_value_for_none(self):
        assert value(INVERSE + "(real v (or? (f 0) 5))", "v") == 5

    def test_equality_with_none(self):
        assert value(INVERSE + "(bool v (= (f 0) none))", "v") is True

    def test_a_parameter_that_allows_none(self):
        assert value("(func g ((real|none x)) (or? x 5)) (real v (g none))", "v") == 5

    @NONE_ARGUMENT
    def test_a_parameter_that_does_not_allow_none(self):
        # Today the body is evaluated, and the call gives 5.
        assert value(INVERSE + "(func h ((real x)) 5) (real|none v (h (f 0)))", "v") is None

    def test_a_list_holds_none(self):
        assert value(INVERSE + "(list[real|none] v {1 (f 0)})", "v") == [1, None]

    def test_a_point_with_a_coordinate_that_is_none_is_none(self):
        assert value(INVERSE + "(point|none v [1 (f 0)])", "v") is None

    def test_if_is_none_only_when_the_branch_taken_is(self):
        assert value(INVERSE + "(real|none v (if (= 1 1) 3 (f 0)))", "v") == 3
        assert value(INVERSE + "(real|none v (if (= 1 2) 3 (f 0)))", "v") is None

    def test_map_passes_none_through(self):
        assert value(INVERSE + "(list[real|none] v (map {1 0} f))", "v") == [1, None]

    @REVERSE
    def test_reverse_passes_none_through(self):
        # Today the compiler stops with a Python TypeError.
        assert value(INVERSE + "(list[real|none] v (reverse {1 (f 0)}))", "v") == [None, 1]

    def test_a_read_of_a_position_passes_none_through(self):
        assert value(INVERSE + "(real|none v (. {1 (f 0)} 1))", "v") is None

    def test_a_part_of_none_is_none(self):
        assert value("(func p ((real x)) {(/ 1 x) 0}) (real|none v (. (p 0) 0))", "v") is None

    def test_an_interpolated_string_with_a_part_that_is_none(self):
        assert value(INVERSE + "(string|none v f'a{(f 0)}')", "v") is None

    @NONE_COLLECTION
    def test_a_collection_function_given_none(self):
        src = "(list[int]|none v (map (if (= 1 2) {1} none) (fn ((int x)) x)))"
        assert value(src, "v") is None
