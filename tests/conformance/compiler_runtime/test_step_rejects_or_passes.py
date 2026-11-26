"""Conformance tests of the rule step-rejects-or-passes (docs/spec/compiler-runtime.md)."""

from ._shared import (
    FIGURE,
    RAND,
    compile_error,
    pytest,
    raw_mtpc,
    rule,
    schema_errors,
    syntax_error,
)


@rule("step-rejects-or-passes")
class TestStepRejectsOrPasses:
    def test_the_parse_step_rejects_with_a_syntax_error(self):
        syntax_error("(real k")

    def test_a_later_step_rejects_with_a_compile_error(self):
        compile_error("(real k j)")

    @pytest.mark.parametrize(
        "src",
        [
            FIGURE,
            RAND + "(rand-seed s 1) (real v (rand))",
            "(real k 0) (button b (animation (move k (to 1) (duration 1))))",
        ],
    )
    def test_an_accepted_source_gives_a_valid_mtpc(self, src):
        assert schema_errors(raw_mtpc(src)) == []
