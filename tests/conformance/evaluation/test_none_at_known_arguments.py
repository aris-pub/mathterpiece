"""Conformance tests of the rule none-at-known-arguments (docs/spec/evaluation.md)."""

from ._shared import (
    COPIES,
    INVERSE,
    RAND,
    RAND_BOUNDS,
    accepted,
    compile_error,
    pytest,
    rule,
    value,
)


@rule("none-at-known-arguments")
class TestNoneAtKnownInputs:
    @pytest.mark.parametrize(
        "src",
        [
            "(real v (sqrt -1))",
            "(real v (or? (sqrt -1) 0))",
            "(real v (/ 1 0))",
            "(scene s (group g (circle c (r 1)))) (real v (. (. g 5) r))",
            "(scene s (foreach i 3 (circle_ (r (/ 1 i)))))",
            "(func[real] f ((real x)) (/ 1 x))",
        ],
    )
    def test_compile_errors(self, src):
        compile_error(src)

    @RAND_BOUNDS
    @pytest.mark.parametrize(
        "src",
        [
            RAND + "(rand-seed sd 1) (int b (rand-int 10 3))",
            RAND + "(rand-seed sd 1) ((int (>= 3) (<= 5)) b (rand-int 5 3))",
        ],
    )
    def test_rand_with_known_bounds_in_the_wrong_order(self, src):
        compile_error(src)

    @COPIES
    def test_a_default_in_the_body_of_a_foreach(self):
        accepted("(scene s (foreach i 3 (circle_ (r (or? (/ 1 i) 1)))))")

    def test_a_folded_call_whose_body_gives_none(self):
        assert value(INVERSE + "(real|none v (f 0))", "v") is None

    def test_a_default_in_the_body_of_a_function(self):
        src = "(func[real] f ((real t)) (let ((b (or? (sqrt t) 0))) (if (> t 0) b 1)))"
        assert value(src + " (real v (f -1))", "v") == 1
