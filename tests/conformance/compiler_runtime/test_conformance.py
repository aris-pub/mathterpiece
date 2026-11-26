"""Conformance tests of the rule conformance (docs/spec/compiler-runtime.md)."""

from ._shared import (
    FIGURE,
    LABEL,
    CompileError,
    _labels,
    compile_source,
    pytest,
    raw_mtpc,
    rule,
    schema_errors,
)


@rule("conformance")
class TestConformance:
    @LABEL
    def test_a_rejected_source_gets_an_error_that_carries_a_label(self):
        with pytest.raises(CompileError) as e:
            compile_source("(real a b) (real b 1)")
        carried = set(getattr(e.value, "rules", ()))
        # The source breaks both rules, so the error may carry either label or both.
        assert carried and carried <= {"declare-before-use", "name-lookup"}
        assert carried <= _labels()

    def test_an_accepted_source_gives_a_valid_mtpc(self):
        assert schema_errors(raw_mtpc(FIGURE)) == []
