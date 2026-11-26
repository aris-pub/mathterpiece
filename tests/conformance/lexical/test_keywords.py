"""Conformance tests of the rule keywords (docs/spec/lexical.md)."""

from ._shared import (
    FORBIDDEN_TODAY,
    KEYWORD_NAMES,
    KEYWORDS,
    NOT_KEYWORDS,
    accepted,
    compile_error,
    pytest,
    rule,
)


@rule("keywords")
class TestKeywords:
    @pytest.mark.parametrize(
        "keyword",
        [pytest.param(k, marks=() if k in FORBIDDEN_TODAY else KEYWORD_NAMES) for k in KEYWORDS],
    )
    def test_a_keyword_is_not_the_name_of_a_variable(self, keyword):
        compile_error(f"(real {keyword} 1)")

    def test_the_operator_dot_is_a_keyword(self):
        compile_error("(func . ((real a)) a)")

    @pytest.mark.parametrize(
        "word",
        [pytest.param(w, marks=KEYWORD_NAMES) if w == "const" else w for w in NOT_KEYWORDS],
    )
    def test_the_heads_of_optional_arguments_and_constraints_are_not_keywords(self, word):
        accepted(f"(real {word} 1)")
