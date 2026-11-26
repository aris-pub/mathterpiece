"""Conformance tests of the rule operations-that-give-none (docs/spec/evaluation.md)."""

from ._shared import (
    FOLDED_NONE,
    GIVES_NONE,
    GIVES_NONE_FOLD_REJECTS,
    PICK,
    RAND,
    accepted,
    pytest,
    rule,
    value,
)


@rule("operations-that-give-none")
class TestOperationsThatGiveNone:
    @pytest.mark.parametrize("body, t, arg", GIVES_NONE)
    def test_a_folded_call_gives_none(self, body, t, arg):
        assert value(f"(func f (({t} x)) {body}) (bool v (none? (f {arg})))", "v") is True

    @FOLDED_NONE
    @pytest.mark.parametrize("body, t, arg", GIVES_NONE_FOLD_REJECTS)
    def test_a_folded_call_gives_none_and_is_not_rejected(self, body, t, arg):
        # Today the compiler rejects the call, as if its inputs were known in the prove step.
        assert value(f"(func f (({t} x)) {body}) (bool v (none? (f {arg})))", "v") is True

    @pytest.mark.parametrize(
        "body, t, arg",
        [
            ("(. {1 2 3} x)", "int", "-3"),
            ("(. {1 2 3} x)", "int", "2"),
            ("(tand x)", "real", "45"),
            ("(sqrt x)", "real", "0"),
            ("(asin x)", "real", "1"),
            ("(asec x)", "real", "1"),
            ("(log 2 x)", "real", "2"),
            ("(min x)", "list[real]", "{1}"),
        ],
    )
    def test_at_every_other_input_there_is_a_value(self, body, t, arg):
        assert value(f"(func f (({t} x)) {body}) (bool v (none? (f {arg})))", "v") is False

    def test_a_result_beyond_the_largest_real_is_not_none(self):
        assert value("(func f ((real x)) (* x x x)) (bool v (none? (f 1e150)))", "v") is False

    @pytest.mark.parametrize(
        "body, arg",
        [("(exp x)", "1000"), ("(^ x 400)", "10.0"), ("(/ 1 x)", "1e-200"), ("(csc x)", "1e-200")],
    )
    def test_an_overflow_is_not_none(self, body, arg):
        assert value(f"(func f ((real x)) {body}) (bool v (none? (f {arg})))", "v") is False

    @pytest.mark.parametrize("src", ["(real k 1) (real v (exp k))", "(real k 1) (real v (^ 2 k))"])
    def test_a_result_that_may_overflow_is_never_none(self, src):
        accepted(src)

    @PICK
    def test_pick_on_a_list_that_is_not_empty_never_gives_none(self):
        accepted(RAND + "(rand-seed sd 1) (real v (pick {1 2}))")

    def test_a_bound_value_that_may_break_its_constraint(self):
        m = accepted("(real k 1 (>= 0) (<= 2)) (real|none v (* 2 k) (<= 3))")
        assert m.get("v").value.expr.op == "check"
