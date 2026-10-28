from fractions import Fraction

import pytest

from mathterpiece.nodes import (
    BoolLit,
    ComplexLit,
    Form,
    InterpStrLit,
    IntLit,
    Name,
    Pos,
    RatioLit,
    RealLit,
    StrLit,
)
from mathterpiece.parse import ParseError, parse


def atom(text):
    """Parse a single atom by wrapping it in a form."""
    (form,) = parse(f"(f {text})")
    assert len(form.items) == 2
    return form.items[1]


def n(*parts):
    return Name(tuple(parts))


def error_at(src):
    with pytest.raises(ParseError) as exc:
        parse(src)
    return exc.value.pos


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

    def test_empty_form_is_error(self):
        with pytest.raises(ParseError):
            parse("()")

    def test_nested_empty_form_is_error(self):
        with pytest.raises(ParseError):
            parse("(a ())")

    def test_unclosed_form_reports_opening_paren(self):
        assert error_at("(a\n  (b c)") == Pos(1, 1)

    def test_unclosed_nested_form_reports_its_opening_paren(self):
        assert error_at("(a\n  (b c") == Pos(2, 3)

    def test_stray_close_paren(self):
        assert error_at("(a) )") == Pos(1, 5)

    @pytest.mark.parametrize("src", ["a", "'a'", "1", "true", "$'a'"])
    def test_toplevel_atom_is_error(self, src):
        with pytest.raises(ParseError):
            parse(src)


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
        with pytest.raises(ParseError):
            atom("1/0")

    @pytest.mark.parametrize("text", ["3/-4", "3/+4", "1.5/2", "1/2.5", "1/", "/2", "1/2/3"])
    def test_invalid_ratio(self, text):
        with pytest.raises(ParseError):
            atom(text)


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
        with pytest.raises(ParseError):
            atom(text)


class TestInvalidNumbers:
    @pytest.mark.parametrize("text", ["2x", "1/2x", "1_000", "0x10", "1.2.3", "1e", "1e+", "3.5f"])
    def test_number_followed_by_other_chars(self, text):
        with pytest.raises(ParseError):
            atom(text)


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
        with pytest.raises(ParseError):
            atom(text)


class TestNames:
    @pytest.mark.parametrize(
        "text",
        [
            "disk",
            "show-label",
            "teal_c",
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
            "2.x",
        ],
    )
    def test_invalid_name(self, text):
        with pytest.raises(ParseError):
            atom(text)

    @pytest.mark.parametrize("ch", ["[", "]", "{", "}"])
    def test_brackets_not_allowed_in_names(self, ch):
        with pytest.raises(ParseError):
            atom(f"a{ch}b")

    @pytest.mark.parametrize("ch", ["[", "]", "{", "}"])
    def test_brackets_outside_strings_are_errors(self, ch):
        with pytest.raises(ParseError):
            parse(f"(a {ch})")

    def test_double_quote_in_name_is_error(self):
        with pytest.raises(ParseError):
            atom('a"b')


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
        with pytest.raises(ParseError):
            atom(f"'a{esc}b'")

    def test_unterminated_reports_opening_quote(self):
        assert error_at("(f 'abc") == Pos(1, 4)

    def test_trailing_backslash_is_unterminated(self):
        with pytest.raises(ParseError):
            parse("(f 'abc\\')")

    def test_followed_directly_by_token_is_error(self):
        with pytest.raises(ParseError):
            parse("(f 'a'b)")

    def test_followed_directly_by_string_is_error(self):
        with pytest.raises(ParseError):
            parse("(f 'a''b')")

    def test_followed_by_close_paren(self):
        assert parse("(f 'a')") == (Form((n("f"), StrLit("a"))),)

    def test_followed_by_open_paren(self):
        assert parse("(f 'a'(g))") == (Form((n("f"), StrLit("a"), Form((n("g"),)))),)

    def test_followed_by_comment(self):
        assert parse("(f 'a';c\n)") == (Form((n("f"), StrLit("a"))),)

    def test_double_quotes_are_errors(self):
        with pytest.raises(ParseError):
            parse('(f "a")')


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
        "text",
        [
            "$'{}'",
            "$'{  }'",
            "$'a } b'",
            "$'a {b'",
            "$'{1}'",
            "$'{a b}'",
            "$'{+}'",
            "$'{-x}'",
            "$'{a.}'",
            "$'{(f)}'",
            "$'{'a'}'",
            r"$'\t'",
        ],
    )
    def test_invalid(self, text):
        with pytest.raises(ParseError):
            atom(text)

    def test_dollar_without_quote_is_error(self):
        with pytest.raises(ParseError):
            atom("$x")

    def test_lone_dollar_is_error(self):
        with pytest.raises(ParseError):
            atom("$")

    def test_unterminated_reports_dollar(self):
        assert error_at("(f $'abc") == Pos(1, 4)

    def test_followed_directly_by_token_is_error(self):
        with pytest.raises(ParseError):
            parse("(f $'a'b)")


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
