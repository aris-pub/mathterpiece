"""Conformance tests of the rule adjacent-items (docs/spec/grammar.md)."""

from ._shared import items, pytest, rule, syntax_error


@rule("adjacent-items")
class TestAdjacentItems:
    @pytest.mark.parametrize("src, count", [("(f a(b)c)", 3), ("(f (a)b)", 2), ("(f 'x'(b))", 2)])
    def test_a_form_needs_no_whitespace_around_it(self, src, count):
        assert len(items(src)) == count

    def test_after_a_prefixed_form_that_ends_with_a_form(self):
        assert len(items("(f free@(g)x)")) == 2

    @pytest.mark.parametrize(
        "src",
        ["(f 'a''b')", "(f [1]x)", "(f 'a'b)", "(f a'b')", "(f 1'a')"],
    )
    def test_other_items_need_whitespace_between_them(self, src):
        syntax_error(src)
