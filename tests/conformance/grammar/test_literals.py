"""Conformance tests of the rule literals (docs/spec/grammar.md)."""

from ._shared import accepted, pytest, rule


@rule("literals")
class TestLiterals:
    @pytest.mark.parametrize(
        "decl",
        [
            "(real w 2.5)",
            "(string w 'crimson')",
            "(bool w true)",
            "(real|none w none)",
            "(list[real] w {0 1})",
            "(list[list[real]] w {{1 2} {3 4}})",
        ],
    )
    def test_a_literal_writes_a_value(self, decl):
        assert accepted(decl).get("w").value.value is not None or "none" in decl
