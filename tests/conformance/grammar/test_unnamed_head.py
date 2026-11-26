"""Conformance tests of the rule unnamed-head (docs/spec/grammar.md)."""

from ._shared import NoneLit, form, forms, mtpc, name, rule


@rule("unnamed-head")
class TestUnnamedHead:
    def test_the_underscore_becomes_none_as_the_second_item(self):
        assert forms("(circle_ (r 1))") == forms("(circle none (r 1))")
        assert forms("(marks.grid_ a)") == forms("(marks.grid none a)")

    def test_a_broadened_type(self):
        assert forms("(line|none_ x)") == forms("(line|none none x)")

    def test_none_underscore(self):
        assert forms("(none_ a)") == (form(NoneLit(), NoneLit(), name("a")),)

    def test_the_two_spellings_compile_the_same(self):
        assert mtpc("(scene s (circle_ (r 1)))") == mtpc("(scene s (circle none (r 1)))")
