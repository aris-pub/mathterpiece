"""The parser (docs/syntax.md): forms, atoms, names, strings, lists, type notation, and the
errors it gives, with their positions. Each file in tests/malformed holds one mistake, and its
first line says the one error it must give: "; error LINE:COL MESSAGE"."""

import re
from fractions import Fraction
from pathlib import Path

import pytest

from mathterpiece.nodes import (
    Bar,
    BoolLit,
    Brackets,
    ComplexLit,
    Field,
    Form,
    InterpStrLit,
    IntLit,
    ListLit,
    Name,
    NoneLit,
    Pos,
    RatioLit,
    RealLit,
    StrLit,
)
from mathterpiece.parse import ParseError, parse

NO_NAME = "_ is not a name: write none, or head_ for a form with no name"
MALFORMED = sorted((Path(__file__).parent / "malformed").glob("*.mtp"))


def atom(text):
    """Parse a single atom by wrapping it in a form."""
    (form,) = parse(f"(f {text})")
    assert len(form.items) == 2
    return form.items[1]


def n(*parts):
    return Name(tuple(parts))


def error_at(src, msg):
    """The position of the error parsing src gives, after checking its message is msg."""
    with pytest.raises(ParseError) as exc:
        parse(src)
    assert exc.value.msg == msg
    return exc.value.pos


def atom_error(text, msg):
    """As error_at, for an atom written inside a form."""
    return error_at(f"(f {text})", msg)


class TestForms:
    def test_single_form(self):
        assert parse("(circle 'a')") == (Form((n("circle"), StrLit("a"))),)

    def test_nested_forms(self):
        assert parse("(circle 'a' (r 1))") == (
            Form((n("circle"), StrLit("a"), Form((n("r"), IntLit(1))))),
        )

    def test_several_toplevel_forms_in_order(self):
        assert parse("(a) (b)\n(c)") == (Form((n("a"),)), Form((n("b"),)), Form((n("c"),)))

    def test_empty_source(self):
        assert parse("") == ()

    def test_only_whitespace_and_comments(self):
        assert parse("  \n\t ; nothing here\n") == ()

    def test_whitespace_inside_forms(self):
        assert parse("(  a\n\t b  )") == (Form((n("a"), n("b"))),)

    def test_adjacent_forms(self):
        assert parse("(a (b)(c))") == (Form((n("a"), Form((n("b"),)), Form((n("c"),)))),)

    def test_unclosed_form_reports_opening_paren(self):
        assert error_at("(a\n  (b c)", "unclosed '('") == Pos(1, 1)

    def test_unclosed_nested_form_reports_its_opening_paren(self):
        assert error_at("(a\n  (b c", "unclosed '('") == Pos(2, 3)

    def test_stray_close_paren(self):
        assert error_at("(a) )", "unexpected ')'") == Pos(1, 5)

    @pytest.mark.parametrize("src", ["a", "'a'", "1", "true", "$'a'"])
    def test_toplevel_atom_is_error(self, src):
        error_at(src, "expected a form at the top level")


class TestComments:
    def test_comment_line(self):
        assert parse("; a comment\n(a)") == (Form((n("a"),)),)

    def test_comment_after_form(self):
        assert parse("(a) ; trailing") == (Form((n("a"),)),)

    def test_comment_inside_form(self):
        assert parse("(a ; inner\n b)") == (Form((n("a"), n("b"))),)

    def test_comment_ends_atom(self):
        assert parse("(a b;comment\n)") == (Form((n("a"), n("b"))),)

    def test_semicolon_inside_string_is_text(self):
        assert atom("'a;b'") == StrLit("a;b")


class TestInt:
    @pytest.mark.parametrize(
        "text, value", [("3", 3), ("0", 0), ("-12", -12), ("+3", 3), ("007", 7)]
    )
    def test_int(self, text, value):
        node = atom(text)
        assert node == IntLit(value)
        assert type(node.value) is int


class TestRatio:
    @pytest.mark.parametrize(
        "text, value",
        [("1/2", Fraction(1, 2)), ("-3/4", Fraction(-3, 4)), ("+3/4", Fraction(3, 4))],
    )
    def test_ratio(self, text, value):
        assert atom(text) == RatioLit(value)

    def test_ratio_is_normalized(self):
        assert atom("2/4") == RatioLit(Fraction(1, 2))

    def test_whole_ratio_stays_ratio(self):
        assert atom("4/2") == RatioLit(Fraction(2))

    def test_zero_denominator_is_error(self):
        atom_error("1/0", "zero denominator in '1/0'")

    @pytest.mark.parametrize("text", ["3/-4", "3/+4", "1.5/2", "1/2.5", "1/", "1/2/3"])
    def test_invalid_ratio(self, text):
        atom_error(text, f"invalid number '{text}'")

    def test_a_slash_first_is_not_a_number(self):
        atom_error("/2", "invalid name '/2'")


class TestReal:
    @pytest.mark.parametrize(
        "text, value",
        [
            ("2.5", 2.5),
            (".5", 0.5),
            ("5.", 5.0),
            ("-0.1", -0.1),
            ("+2.5", 2.5),
            ("-.5", -0.5),
            ("1e-3", 1e-3),
            ("1E3", 1e3),
            ("2.5e+10", 2.5e10),
            ("1e3", 1000.0),
        ],
    )
    def test_real(self, text, value):
        node = atom(text)
        assert node == RealLit(value)
        assert type(node.value) is float


class TestComplex:
    @pytest.mark.parametrize(
        "text, value",
        [
            ("3+4i", 3 + 4j),
            ("3-4i", 3 - 4j),
            ("2i", 2j),
            ("-2i", -2j),
            ("+2i", 2j),
            (".5i", 0.5j),
            ("-1.5-2i", -1.5 - 2j),
            ("1e3+2e-1i", 1000 + 0.2j),
            ("1e-3i", 1e-3j),
            ("1i", 1j),
        ],
    )
    def test_complex(self, text, value):
        assert atom(text) == ComplexLit(value)

    @pytest.mark.parametrize("text", ["3+i", "3+4", "3+4j", "2ii", "1/2i", "3+4i5"])
    def test_invalid_complex(self, text):
        atom_error(text, f"invalid number '{text}'")


class TestInvalidNumbers:
    @pytest.mark.parametrize("text", ["2x", "1/2x", "1_000", "0x10", "1.2.3", "1e", "1e+", "3.5f"])
    def test_number_followed_by_other_chars(self, text):
        atom_error(text, f"invalid number '{text}'")


class TestBool:
    def test_true(self):
        assert atom("true") == BoolLit(True)

    def test_false(self):
        assert atom("false") == BoolLit(False)

    @pytest.mark.parametrize("text", ["True", "False", "truex", "xtrue"])
    def test_lookalikes_are_names(self, text):
        assert atom(text) == n(text)


class TestOperators:
    @pytest.mark.parametrize("op", ["+", "-", "*", "/", "^", "<", "<=", ">", ">=", "=", "!="])
    def test_operator_is_one_part_name(self, op):
        assert atom(op) == n(op)

    def test_operator_as_head(self):
        assert parse("(+ a 1)") == (Form((n("+"), n("a"), IntLit(1))),)

    @pytest.mark.parametrize("text", ["--", "->", "++", "<>", "==", "=>", "**", "+-", "<=="])
    def test_unknown_operator_like_token_is_error(self, text):
        atom_error(text, f"invalid name '{text}'")


class TestNames:
    @pytest.mark.parametrize(
        "text",
        [
            "disk",
            "show-label",
            "visible?",
            "set!",
            "a->b",
            "x'",
            "f'",
            "g''",
            "f'oo'",
            "x2",
            "α₁",
            "∂f",
            "∇φ",
            "ℝ",
            "x′",
            "δ",
            "∞",
            "!x",
            "a+b",
            "a*b",
            "a<b",
            "a=b",
        ],
    )
    def test_valid_name(self, text):
        assert atom(text) == n(text)

    def test_dotted_name(self):
        assert atom("disk.r") == n("disk", "r")

    def test_long_dotted_name(self):
        assert atom("ldisk.crc.x") == n("ldisk", "crc", "x")

    def test_dotted_name_with_unicode_and_primes(self):
        assert atom("α₁.x'") == n("α₁", "x'")

    @pytest.mark.parametrize(
        "text",
        [
            "-x",
            "+x",
            "*x",
            "<x",
            ">x",
            "=x",
            "^x",
            "x^2",
            "a/b",
            "a$b",
            ".x",
            "x.",
            "a..b",
            "a.1",
            "a.-b",
            "teal_c",
        ],
    )
    def test_invalid_name(self, text):
        atom_error(text, f"invalid name '{text}'")

    def test_a_digit_first_is_read_as_a_number(self):
        atom_error("2.x", "invalid number '2.x'")

    def test_an_underscore_alone(self):
        atom_error("_", NO_NAME)

    @pytest.mark.parametrize(
        "ch, msg",
        [
            ("[", "expected ']' after '['"),
            ("]", "unexpected ']'"),
            ("{", "'{' is reserved"),
            ("}", "'}' is reserved"),
        ],
    )
    def test_brackets_not_allowed_in_names(self, ch, msg):
        atom_error(f"a{ch}b", msg)

    @pytest.mark.parametrize(
        "ch, msg",
        [
            ("[", "expected ']' to close the list"),
            ("]", "unexpected ']'"),
            ("{", "'{' is reserved"),
            ("}", "'}' is reserved"),
        ],
    )
    def test_unmatched_brackets_outside_strings_are_errors(self, ch, msg):
        error_at(f"(a {ch})", msg)

    def test_double_quote_in_name_is_error(self):
        atom_error('a"b', "double quotes are not allowed; use single quotes")


class TestStr:
    def test_simple(self):
        assert atom("'hello'") == StrLit("hello")

    def test_empty(self):
        assert atom("''") == StrLit("")

    def test_spaces_and_parens_inside(self):
        assert atom("'hello (big) world'") == StrLit("hello (big) world")

    def test_unicode(self):
        assert atom("'ρ ≤ δ/2 ✓'") == StrLit("ρ ≤ δ/2 ✓")

    def test_raw_line_break(self):
        assert atom("'line one\nline two'") == StrLit("line one\nline two")

    @pytest.mark.parametrize(
        "text, value",
        [(r"'it\'s'", "it's"), (r"'a\\b'", "a\\b"), (r"'a\nb'", "a\nb"), (r"'\\n'", "\\n")],
    )
    def test_escapes(self, text, value):
        assert atom(text) == StrLit(value)

    @pytest.mark.parametrize("esc", [r"\t", r"\r", r"\0", r"\"", r"\q", "\\" + "u0041", r"\x41"])
    def test_other_escapes_are_errors(self, esc):
        atom_error(f"'a{esc}b'", f"invalid escape '{esc[:2]}'")

    def test_unterminated_reports_opening_quote(self):
        assert error_at("(f 'abc", "unterminated string") == Pos(1, 4)

    def test_trailing_backslash_is_unterminated(self):
        error_at("(f 'abc\\')", "unterminated string")

    def test_followed_directly_by_token_is_error(self):
        error_at("(f 'a'b)", "expected whitespace, '(', ')' or ';' after a string")

    def test_followed_directly_by_string_is_error(self):
        error_at("(f 'a''b')", "expected whitespace, '(', ')' or ';' after a string")

    def test_followed_by_close_paren(self):
        assert parse("(f 'a')") == (Form((n("f"), StrLit("a"))),)

    def test_followed_by_open_paren(self):
        assert parse("(f 'a'(g))") == (Form((n("f"), StrLit("a"), Form((n("g"),)))),)

    def test_followed_by_comment(self):
        assert parse("(f 'a';c\n)") == (Form((n("f"), StrLit("a"))),)

    def test_double_quotes_are_errors(self):
        error_at('(f "a")', "double quotes are not allowed; use single quotes")


class TestInterpStr:
    def test_plain_text(self):
        assert atom("$'plain'") == InterpStrLit(("plain",))

    def test_empty(self):
        assert atom("$''") == InterpStrLit(())

    def test_name(self):
        assert atom("$'dot{i}'") == InterpStrLit(("dot", n("i")))

    def test_dotted_name(self):
        assert atom("$'r = {disk.r}'") == InterpStrLit(("r = ", n("disk", "r")))

    def test_several_names(self):
        assert atom("$'{a} and {b}'") == InterpStrLit((n("a"), " and ", n("b")))

    def test_adjacent_names(self):
        assert atom("$'{a}{b}'") == InterpStrLit((n("a"), n("b")))

    def test_whitespace_inside_braces(self):
        assert atom("$'x { i } y'") == InterpStrLit(("x ", n("i"), " y"))

    def test_line_break_inside_braces(self):
        assert atom("$'{\n i\n}'") == InterpStrLit((n("i"),))

    def test_literal_braces(self):
        assert atom("$'{{x}} and {{'") == InterpStrLit(("{x} and {",))

    def test_literal_braces_next_to_name(self):
        assert atom("$'{{{i}}}'") == InterpStrLit(("{", n("i"), "}"))

    def test_escapes(self):
        assert atom(r"$'it\'s {x}\n'") == InterpStrLit(("it's ", n("x"), "\n"))

    def test_unicode_name(self):
        assert atom("$'{α₁}'") == InterpStrLit((n("α₁"),))

    @pytest.mark.parametrize(
        "text, msg",
        [
            ("$'{}'", "expected an expression inside braces"),
            ("$'{  }'", "expected an expression inside braces"),
            ("$'a } b'", "unmatched '}'; write '}}' for a literal brace"),
            ("$'a {b'", "expected a single expression and '}' inside braces"),
            ("$'{a b}'", "expected a single expression and '}' inside braces"),
            ("$'{-x}'", "invalid name '-x'"),
            ("$'{a.}'", "invalid name 'a.'"),
            (r"$'\t'", r"invalid escape '\t'"),
        ],
    )
    def test_invalid(self, text, msg):
        atom_error(text, msg)

    def test_dollar_without_quote_is_error(self):
        atom_error("$x", "'$' must be followed by a quote")

    def test_lone_dollar_is_error(self):
        atom_error("$", "'$' must be followed by a quote")

    def test_unterminated_reports_dollar(self):
        assert error_at("(f $'abc", "unterminated string") == Pos(1, 4)

    def test_followed_directly_by_token_is_error(self):
        error_at("(f $'a'b)", "expected whitespace, '(', ')' or ';' after a string")


class TestNone:
    def test_none(self):
        assert atom("none") == NoneLit()

    def test_lookalikes_are_names(self):
        assert atom("none?") == n("none?")
        assert atom("nonesuch") == n("nonesuch")

    def test_in_a_list(self):
        assert atom("[1 none]") == ListLit((IntLit(1), NoneLit()))


class TestExpressionsInBraces:
    # Each {…} in an interpolated string is an expression (syntax.md, section 2).
    @pytest.mark.parametrize(
        "text, part",
        [
            ("$'{1}'", IntLit(1)),
            ("$'{(f x)}'", Form((n("f"), n("x")))),
            ("$'{'a'}'", StrLit("a")),
            ("$'{none}'", NoneLit()),
            ("$'{+}'", n("+")),
            ("$'{[0 1]}'", ListLit((IntLit(0), IntLit(1)))),
            ("$'{(or? x 0):.2f}'", Field(Form((n("or?"), n("x"), IntLit(0))), ".2f")),
            ("$'{ (f x) :>8}'", Field(Form((n("f"), n("x"))), ">8")),
        ],
    )
    def test_any_expression(self, text, part):
        assert atom(text) == InterpStrLit((part,))

    def test_a_string_inside_braces_has_its_own_quotes(self):
        assert atom("$'a {(or? x 'n/a')} b'") == InterpStrLit(
            ("a ", Form((n("or?"), n("x"), StrLit("n/a"))), " b")
        )


class TestPartForm:
    # (. X Y) reads a part of what any expression gives (syntax.md, section 7).
    def test_dot_is_a_head(self):
        (form,) = parse("(f (. (g x) r))")
        assert form.items[1] == Form((n("."), Form((n("g"), n("x"))), n("r")))

    def test_with_a_position(self):
        assert atom("(. (g x) 0)") == Form((n("."), Form((n("g"), n("x"))), IntLit(0)))

    def test_a_part_cannot_follow_a_form(self):
        error_at("(f (g x).r)", "a part cannot follow a form; use (. X Y)")

    def test_a_bracket_cannot_follow_a_form(self):
        error_at("(f (g x)[0])", "a part cannot follow a form; use (. X Y)")


class TestIndexing:
    @pytest.mark.parametrize(
        "text, parts",
        [
            ("g[0]", ("g", IntLit(0))),
            ("g[-1]", ("g", IntLit(-1))),
            ("g[i]", ("g", n("i"))),
            ("g['k']", ("g", StrLit("k"))),
            ("g[(+ i 1)]", ("g", Form((n("+"), n("i"), IntLit(1))))),
            ("g[ 0 ]", ("g", IntLit(0))),
            ("g[\n  0\n]", ("g", IntLit(0))),
            ("g[0 ; comment\n]", ("g", IntLit(0))),
            ("g[0].r", ("g", IntLit(0), "r")),
            ("g[0].r.s", ("g", IntLit(0), "r", "s")),
            ("g[0].r[1]", ("g", IntLit(0), "r", IntLit(1))),
            ("a.b[0].c", ("a", "b", IntLit(0), "c")),
            ("g[0][1]", ("g", IntLit(0), IntLit(1))),
            ("g[h[0]]", ("g", n("h", IntLit(0)))),
            ("g[h[0].k]", ("g", n("h", IntLit(0), "k"))),
            ("α₁[0].x'", ("α₁", IntLit(0), "x'")),
        ],
    )
    def test_valid(self, text, parts):
        assert atom(text) == Name(parts)

    def test_in_a_form(self):
        assert parse("(f g[0] h)") == (Form((n("f"), n("g", IntLit(0)), n("h"))),)

    def test_before_close_paren(self):
        assert parse("(f g[0])") == (Form((n("f"), n("g", IntLit(0)))),)

    @pytest.mark.parametrize(
        "text, msg",
        [
            ("g[]", "empty index"),
            ("g[ ]", "empty index"),
            ("g[0", "expected ']' after '['"),
            ("g[0]x", "unexpected 'x' after index"),
            ("g[0].", "expected a name after '.'"),
            ("g[0]..r", "invalid name '.r'"),
            ("g[0].1", "invalid name '1'"),
            ("g[0]]", "unexpected ']'"),
            ("g.[0]", "invalid name 'g.'"),
            ("1[0]", "only names can be indexed, got '1'"),
            ("1.5[0]", "only names can be indexed, got '1.5'"),
            ("true[0]", "only names can be indexed, got 'true'"),
            ("+[0]", "only names can be indexed, got '+'"),
            ("g]", "unexpected ']'"),
            ("g[0]'a'", 'unexpected "\'" after index'),
        ],
    )
    def test_invalid(self, text, msg):
        atom_error(text, msg)

    def test_unclosed_reports_opening_bracket(self):
        assert error_at("(f g[0\n  h)", "expected ']' after '['") == Pos(1, 5)

    def test_index_position(self):
        (form,) = parse("(f g[ 12 ])")
        name = form.items[1]
        assert isinstance(name, Name)
        assert name.pos == Pos(1, 4)
        index = name.parts[1]
        assert isinstance(index, IntLit)
        assert index.pos == Pos(1, 7)

    @pytest.mark.parametrize(
        "text, parts",
        [
            ("$'{g[0].r}'", (n("g", IntLit(0), "r"),)),
            ("$'{ g[ i ] }'", (n("g", n("i")),)),
            ("$'{g[(+ i 1)]}'", (n("g", Form((n("+"), n("i"), IntLit(1)))),)),
            ("$'{g['a']}'", (n("g", StrLit("a")),)),
            ("$'x {g[0]} y'", ("x ", n("g", IntLit(0)), " y")),
        ],
    )
    def test_inside_interpolated_string(self, text, parts):
        assert atom(text) == InterpStrLit(parts)

    @pytest.mark.parametrize(
        "text, msg",
        [
            ("$'{g [0]}'", "expected a single expression and '}' inside braces"),
            ("$'{g[0]x}'", "unexpected 'x' after index"),
            ("$'{g[0}'", "expected ']' after '['"),
        ],
    )
    def test_invalid_inside_interpolated_string(self, text, msg):
        atom_error(text, msg)


class TestPositions:
    def test_form_position_is_opening_paren(self):
        (form,) = parse("\n  (a b)")
        assert form.pos == Pos(2, 3)

    def test_atom_positions(self):
        (form,) = parse("(circle 'a'\n  (r 1.5) $'x{i}' true)")
        head, name, r, interp, flag = form.items
        assert head.pos == Pos(1, 2)
        assert name.pos == Pos(1, 9)
        assert isinstance(r, Form)
        assert r.pos == Pos(2, 3)
        assert r.items[0].pos == Pos(2, 4)
        assert r.items[1].pos == Pos(2, 6)
        assert interp.pos == Pos(2, 11)
        assert flag.pos == Pos(2, 19)

    def test_columns_count_unicode_characters(self):
        (form,) = parse("(f 'αβγ' x)")
        assert form.items[2].pos == Pos(1, 10)

    def test_line_breaks_inside_strings_advance_lines(self):
        (form,) = parse("(f 'a\nbc' x)")
        assert form.items[2].pos == Pos(2, 5)

    def test_name_inside_interp_has_position(self):
        (form,) = parse("(f $'ab{ x }')")
        interp = form.items[1]
        assert isinstance(interp, InterpStrLit)
        (_, name) = interp.parts
        assert isinstance(name, Name)
        assert name.pos == Pos(1, 10)

    def test_position_does_not_count_toward_equality(self):
        assert Name(("a",), Pos(1, 1)) == Name(("a",), Pos(5, 9))

    def test_error_position_and_message(self):
        with pytest.raises(ParseError) as exc:
            parse("(f\n  2x)")
        assert exc.value.pos == Pos(2, 3)
        assert str(exc.value).startswith("2:3: ")


class TestNodes:
    def test_nodes_are_frozen(self):
        node = IntLit(1)
        with pytest.raises(AttributeError):
            node.value = 2  # ty: ignore[invalid-assignment]


class TestListLiteral:
    @pytest.mark.parametrize(
        "text, items",
        [
            ("[1 2]", (IntLit(1), IntLit(2))),
            ("[1 2 3]", (IntLit(1), IntLit(2), IntLit(3))),
            ("[]", ()),
            ("[ 1.5\n -2 ]", (RealLit(1.5), IntLit(-2))),
            ("[k (* 2 k)]", (n("k"), Form((n("*"), IntLit(2), n("k"))))),
            ("[a.x g[0].r]", (n("a", "x"), n("g", IntLit(0), "r"))),
            ("[[1 2] 3]", (ListLit((IntLit(1), IntLit(2))), IntLit(3))),
        ],
    )
    def test_items(self, text, items):
        assert atom(text) == ListLit(items)

    def test_a_space_separates_a_name_from_a_list(self):
        (form,) = parse("(f g [0])")
        assert form.items[1:] == (n("g"), ListLit((IntLit(0),)))

    def test_no_space_indexes(self):
        assert atom("g[0]") == n("g", IntLit(0))

    def test_position(self):
        (form,) = parse("(f\n  [1 2])")
        assert form.items[1].pos == Pos(2, 3)

    @pytest.mark.parametrize(
        "src, msg",
        [
            ("(f [1 2)", "expected ']' to close the list"),
            ("(f [1", "unclosed '['"),
            ("(f ])", "unexpected ']'"),
            ("(f [1]x)", "unexpected 'x' after a list"),
        ],
    )
    def test_invalid(self, src, msg):
        error_at(src, msg)

    def test_not_at_the_top_level(self):
        error_at("[1 2]", "expected a form at the top level")


class TestFormatSpecs:
    @pytest.mark.parametrize(
        "text, field",
        [
            ("$'{x:.2f}'", Field(n("x"), ".2f")),
            ("$'{g[0].r:>8.3f}'", Field(n("g", IntLit(0), "r"), ">8.3f")),
            ("$'{x: >5}'", Field(n("x"), " >5")),
            ("$'{ x :.1%}'", Field(n("x"), ".1%")),
        ],
    )
    def test_field(self, text, field):
        assert atom(text) == InterpStrLit((field,))

    def test_with_text_around(self):
        assert atom("$'area {a:.2f} m'") == InterpStrLit(("area ", Field(n("a"), ".2f"), " m"))

    def test_no_spec_stays_a_name(self):
        assert atom("$'{x}'") == InterpStrLit((n("x"),))

    @pytest.mark.parametrize(
        "text, msg",
        [
            ("$'{x:{y}}'", "a format spec cannot hold braces"),
            ("$'{x:.2f'", "expected a single expression and '}' inside braces"),
            ("$'{:.2f}'", "expected an expression inside braces"),
        ],
    )
    def test_invalid(self, text, msg):
        atom_error(text, msg)


class TestTypeNotation:
    # The parser reads type notation as syntax only; the compiler decides from where it sits
    # whether list[color] is a type or a part read (type-system.md, section 5.a).
    @pytest.mark.parametrize(
        "text, node",
        [
            ("real|none", Bar((n("real"), NoneLit()))),
            ("list[real]|none", Bar((n("list", n("real")), NoneLit()))),
            ("list[real|none]", n("list", Bar((n("real"), NoneLit())))),
            ("func[real real]", n("func", Brackets((n("real"), n("real"))))),
            ("func[real shape real]", n("func", Brackets((n("real"), n("shape"), n("real"))))),
            ("list[list[real]]", n("list", n("list", n("real")))),
            (
                "list[(real (>= 0))]",
                n("list", Form((n("real"), Form((n(">="), IntLit(0)))))),
            ),
            ("func[real list[real]]", n("func", Brackets((n("real"), n("list", n("real")))))),
        ],
    )
    def test_types(self, text, node):
        assert atom(text) == node

    def test_a_type_form_heads_a_declaration(self):
        (form,) = parse("((real (>= 0)) r 1)")
        assert form.items[0] == Form((n("real"), Form((n(">="), IntLit(0)))))

    def test_maybe_is_a_form(self):
        assert atom("(maybe real)") == Form((n("maybe"), n("real")))

    def test_several_items_in_a_part_read_parse(self):
        # Only the compiler knows g[0 1] is not in a type position, so it rejects it there.
        assert atom("g[0 1]") == n("g", Brackets((IntLit(0), IntLit(1))))

    def test_a_part_read_is_unchanged(self):
        assert atom("xs[0]") == n("xs", IntLit(0))

    @pytest.mark.parametrize(
        "text, msg",
        [
            ("real|", "expected a type after '|'"),
            ("|none", "unexpected '|'"),
            ("real |none", "unexpected '|'"),
            ("real| none", "expected a type after '|'"),
            ("a||b", "expected a type after '|'"),
        ],
    )
    def test_invalid(self, text, msg):
        atom_error(text, msg)


def test_an_empty_form():
    # () is an empty list of parameters or bindings; the compiler decides where it may go.
    (form,) = parse("(motif m () (circle c))")
    assert form.items[2] == Form(())


class TestParsingNoName:
    # syntax.md "Names": (head_ …) is (head none …), for any form that takes a name; _ is not a
    # name. test_shapes.py has what the compiler makes of it.
    def test_a_head_ending_in_an_underscore_has_no_name(self):
        assert parse("(circle_ (r 1))") == parse("(circle none (r 1))")
        assert parse("(line|none_ (to [1 0]))") == parse("(line|none none (to [1 0]))")
        # mtp-vt25: a motif of a file imported whole.
        assert parse("(marks.grid_ (step 2))") == parse("(marks.grid none (step 2))")

    def test_an_underscore_alone_is_not_a_name(self):
        error_at(
            "(circle _ (r 1))", "_ is not a name: write none, or head_ for a form with no name"
        )

    def test_a_name_holds_no_underscore(self):
        error_at("(real a_b 1)", "invalid name 'a_b'")


class TestParsingIndexingAListWrittenInPlace:
    # mtp-4vx: [a b c][h] is (. [a b c] h). test_compile_core.py has what the compiler makes of it;
    # TestPartForm has (f (g x)[0]), which is an error.
    def test_a_list_then_a_position(self):
        e = atom("[a b c][h]")
        assert isinstance(e, Form)
        assert e.items[0] == Name((".",))
        assert isinstance(e.items[1], ListLit) and e.items[2] == Name(("h",))

    def test_positions_one_after_another(self):
        e = atom("[[1 2] [3 4]][1][0]")
        assert e.items[0] == Name((".",)) and e.items[2] == IntLit(0)
        inner = e.items[1]
        assert isinstance(inner, Form) and inner.items[2] == IntLit(1)

    def test_one_expression_in_the_brackets(self):
        error_at("(f [a b][0 1])", "brackets after a list hold one position")


@pytest.mark.parametrize("path", MALFORMED, ids=[f.stem for f in MALFORMED])
def test_a_malformed_file_gives_one_error_where_it_is(path):
    src = path.read_text()
    m = re.match(r"; error (\d+):(\d+) (.*)\n", src)
    assert m, f"{path.name} does not say its error"
    assert error_at(src, m[3]) == Pos(int(m[1]), int(m[2]))


class TestNameStrings:
    # The author, 2026-11-06: #'dot-{k}' is (name $'dot-{k}'): values filled into the string,
    # which is then read as a name. Parts may follow it. One with nothing to fill in is an
    # error: write the name itself, or (name 'text').
    def test_it_is_the_name_form(self):
        assert parse("(f #'dot-{k}')") == parse("(f (name $'dot-{k}'))")

    def test_parts_may_follow(self):
        assert parse("(f #'dot-{k}'.pos)") == parse("(f (. (name $'dot-{k}') pos))")
        assert parse("(f #'row-{i}'[0].x)") == parse("(f (. (. (name $'row-{i}') 0) x))")

    def test_with_nothing_to_fill_in(self):
        error_at(
            "(f #'dot')",
            "a name string fills values into a name: with none, write the"
            " name itself, or (name 'text')",
        )

    def test_hash_is_not_in_names(self):
        error_at("(real a#b 1)", "invalid name 'a#b'")
        error_at("(f #x)", "'#' starts a name string: #'dot-{k}'")
