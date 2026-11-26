"""Conformance tests of the rule form-template (docs/spec/grammar.md)."""

from ._shared import accepted, compile_error, pytest, rule


@rule("form-template")
class TestFormTemplate:
    @pytest.mark.parametrize(
        "src",
        [
            "(real k 1 (>= 0))",
            "(list[color] cs {#'red' #'blue'})",
            "(func[real] f ((real x)) x)",
            "(real|none k none)",
            "((real (>= 0)) r 1)",
            "(scene s (circle c (r 1) (fill #'red')))",
        ],
    )
    def test_heads_of_each_kind(self, src):
        accepted(src)

    def test_a_form_head_gives_a_type(self):
        compile_error("((real (>= 0)) r -1)")
