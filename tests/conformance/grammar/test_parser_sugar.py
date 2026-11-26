"""Conformance tests of the rule parser-sugar (docs/spec/grammar.md)."""

from ._shared import IntLit, ListLit, StrLit, dot, form, interp, items, name, rule


@rule("parser-sugar")
class TestParserSugar:
    def test_docstring(self):
        assert items("(f doc@'text')") == (form(name("doc"), StrLit("text")),)

    def test_prefixed_form(self):
        assert items("(f r@1)") == (form(name("r"), IntLit(1)),)
        assert items("(f free@x)") == (form(name("free"), name("x")),)

    def test_name_string(self):
        n = form(name("name"), interp(("dot-", name("k"))))
        assert items("(f @'dot-{k}')") == (n,)
        assert items("(f @'dot-{k}'.a.b)") == (dot(dot(n, name("a")), name("b")),)
        assert items("(f @'dot-{k}'[i])") == (dot(n, name("i")),)

    def test_brackets_after_a_list(self):
        assert items("(f {a b c}[h])") == (
            dot(ListLit((name("a"), name("b"), name("c"))), name("h")),
        )

    def test_the_position_of_the_form_is_its_first_character(self):
        (s,) = items("(f  doc@'x')")
        assert (s.pos.line, s.pos.col) == (1, 5)
        (s,) = items("(f  @'d-{k}'.a)")
        inner = s.items[1]
        assert (inner.pos.line, inner.pos.col) == (1, 5)

    def test_a_dot_form_after_a_name_string_has_the_position_of_its_dot(self):
        (s,) = items("(f @'d-{k}'.a[0])")
        assert (s.pos.line, s.pos.col) == (1, 14)
        assert (s.items[1].pos.line, s.items[1].pos.col) == (1, 12)
