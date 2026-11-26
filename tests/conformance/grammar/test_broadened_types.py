"""Conformance tests of the rule broadened-types (docs/spec/grammar.md)."""

from ._shared import Bar, NoneLit, accepted, items, name, pytest, rule, syntax_error


@rule("broadened-types")
class TestBroadenedTypes:
    def test_words_joined_by_a_bar(self):
        assert items("(f real|none a|b|c)") == (
            Bar((name("real"), NoneLit())),
            Bar((name("a"), name("b"), name("c"))),
        )

    @pytest.mark.parametrize("src", ["(f a| b)", "(f a |b)", "(f a||b)", "(f a|'b')", "(f a|(b))"])
    def test_no_whitespace_and_only_words(self, src):
        syntax_error(src)

    def test_the_compiler_reads_it_as_a_type(self):
        m = accepted("(real|none k none)")
        assert m.get("k").value.value is None
