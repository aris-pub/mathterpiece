"""Conformance tests for docs/spec/lexical.md."""

from fractions import Fraction

import pytest

from mathterpiece.cli import main
from mathterpiece.nodes import (
    BoolLit,
    ComplexLit,
    Field,
    Form,
    InterpStrLit,
    IntLit,
    NoneLit,
    RatioLit,
    RealLit,
    StrLit,
)

from .support import (
    accepted,
    compile_error,
    form,
    forms,
    items,
    name,
    syntax_error,
)

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


WHITESPACE = xfail("mtp-ydd4.7.2", "the parser reads every str.isspace() character as whitespace")
NAMES = xfail("mtp-ydd4.7.3", "the parser allows more characters in a name than the rule")
DIGITS = xfail("mtp-ydd4.7.4", "the parser reads every Unicode decimal digit as a digit")
LITERAL_PARTS = xfail("mtp-ydd4.7.32", "the parser reads true, false or none as a part of a name")
UNICODE_CONSTANTS = xfail("mtp-ydd4.7.33", "the built-ins declare the constants π, τ and ∞")
KEYWORD_NAMES = xfail("mtp-ydd4.7.35", "the compiler forbids only a few names, not every keyword")
NESTED_BRACES = xfail("mtp-kzx2", "the parser leaves braces when a string nested in them ends")
BRACE_COMMENTS = xfail("mtp-ydd4.7.31", "the parser skips a comment around the braced expression")


@rule("grammar-in-context")
class TestGrammarInContext:
    def test_a_word_that_starts_with_true_is_one_name(self):
        assert items("(f truex)") == (name("truex"),)

    def test_the_longest_number_is_read(self):
        assert items("(f 1/2 1.5 2i)") == (
            RatioLit(Fraction(1, 2)),
            RealLit(1.5),
            ComplexLit(complex(0, 2)),
        )

    def test_a_head_with_an_underscore_is_read_only_where_a_head_may_be(self):
        assert forms("(circle_ (r 1))") == (
            form(name("circle"), NoneLit(), form(name("r"), IntLit(1))),
        )

    @NAMES
    def test_the_same_text_as_an_argument_is_an_error(self):
        syntax_error("(f circle_)")


@rule("source-text")
class TestSourceText:
    def test_a_file_is_read_with_universal_newlines(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_bytes(b"(string v 'a\r\nb\rc')\r\n")
        main(["compile", str(src)])
        import json

        d = json.loads((tmp_path / "f.mtpc").read_text(encoding="utf-8"))
        assert d["objects"][d["names"]["v"]]["value"]["free"] == "a\nb\nc"

    def test_a_byte_order_mark_at_the_start_is_ignored(self):
        assert forms("﻿(f)") == forms("(f)")

    def test_a_file_that_starts_with_a_byte_order_mark_compiles(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_bytes("﻿(real v 1)\n".encode())
        main(["compile", str(src)])
        assert (tmp_path / "f.mtpc").exists()

    def test_a_byte_order_mark_between_forms_is_an_error(self):
        syntax_error("(f)﻿(g)")

    def test_a_byte_order_mark_inside_a_form_is_an_error(self):
        syntax_error("(f ﻿ a)")

    def test_other_text_is_kept_as_written(self):
        assert items("(f 'é ∑ θ')") == (StrLit("é ∑ θ"),)


@rule("expression-positions")
class TestExpressionPositions:
    def test_line_and_column_count_from_1(self):
        (f,) = forms("(f\n  (g)\tx)")
        assert (f.pos.line, f.pos.col) == (1, 1)
        g, x = f.items[1:]
        assert (g.pos.line, g.pos.col) == (2, 3)
        # A tab adds 1 to the column, like every character but a line feed.
        assert (x.pos.line, x.pos.col) == (2, 7)

    def test_a_byte_order_mark_at_the_start_is_not_counted(self):
        (f,) = forms("﻿(f)")
        assert (f.pos.line, f.pos.col) == (1, 1)


@rule("whitespace-and-comments")
class TestWhitespaceAndComments:
    def test_the_three_whitespace_characters_separate_items(self):
        assert items("(f a\tb\nc d)") == tuple(name(c) for c in "abcd")

    def test_a_comment_runs_to_the_next_line_feed(self):
        assert forms("(f ; a comment (g)\n a)") == forms("(f a)")

    def test_a_comment_may_end_the_source(self):
        assert forms("(f a) ; the end") == forms("(f a)")

    def test_inside_a_string_a_semicolon_and_whitespace_are_text(self):
        assert items("(f 'a ; b\tc')") == (StrLit("a ; b\tc"),)

    @pytest.mark.parametrize(
        "ch",
        [
            pytest.param(" ", id="no-break-space", marks=WHITESPACE),
            pytest.param(" ", id="line-separator", marks=WHITESPACE),
            pytest.param("\x0c", id="form-feed", marks=WHITESPACE),
            pytest.param("\x0b", id="vertical-tab", marks=WHITESPACE),
            pytest.param("　", id="ideographic-space", marks=WHITESPACE),
        ],
    )
    def test_other_space_characters_are_errors(self, ch):
        syntax_error(f"(f a{ch}b)")


@rule("word-ends")
class TestWordEnds:
    @pytest.mark.parametrize("src", ["(f a$'x')", "(f 1x)", "(f a#'x')"])
    def test_text_that_is_not_one_word_is_an_error(self, src):
        syntax_error(src)

    @NAMES
    def test_a_quote_does_not_end_a_word(self):
        syntax_error("(f a'b)")

    def test_a_word_ends_at_a_parenthesis_a_bracket_a_semicolon_or_a_bar(self):
        assert items("(f a(g))") == (name("a"), form(name("g")))
        assert items("(f a;c\n)") == (name("a"),)

    @NAMES
    def test_a_word_ends_at_a_colon(self):
        syntax_error("(f a:b)")


@rule("no-name-part-after-form")
class TestNoPartAfterForm:
    @pytest.mark.parametrize("src", ["(f (sort xs).x)", "(f (sort xs)[0])"])
    def test_a_part_after_a_form_is_an_error(self, src):
        syntax_error(src)

    def test_a_part_of_a_form_is_read_with_the_dot_form(self):
        assert items("(f (. (sort xs) 0))") == (
            form(name("."), form(name("sort"), name("xs")), IntLit(0)),
        )


NAMES_OK = [
    "theta",
    "show-tan",
    "x2",
    "a-",
    "none?",
    "the-true-value",
    "truex",
    "p.empty?",
    "found?.x",
    "ball.on-floor?",
    "Ab",
]


@rule("name-characters")
class TestNameCharacters:
    @pytest.mark.parametrize("text", NAMES_OK)
    def test_names(self, text):
        assert items(f"(f {text})") == (name(*text.split(".")),)

    @pytest.mark.parametrize(
        "text",
        [
            "2x",
            "-x",
            pytest.param("a?b", marks=NAMES),
            pytest.param("x'", marks=NAMES),
            pytest.param("a!b", marks=NAMES),
            pytest.param("a*b", marks=NAMES),
            pytest.param("a=b", marks=NAMES),
            pytest.param("a:b", marks=NAMES),
            pytest.param("θ", marks=NAMES),
            pytest.param("π", marks=NAMES),
            pytest.param("x²", marks=NAMES),
            pytest.param("ünï", marks=NAMES),
        ],
    )
    def test_not_names(self, text):
        syntax_error(f"(f {text})")

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("true.x", marks=LITERAL_PARTS),
            pytest.param("p.true", marks=LITERAL_PARTS),
            pytest.param("none.x", marks=LITERAL_PARTS),
            pytest.param("xs[0].none", marks=LITERAL_PARTS),
            pytest.param("none[0]", marks=LITERAL_PARTS),
        ],
    )
    def test_a_part_that_is_true_false_or_none_is_an_error(self, text):
        syntax_error(f"(f {text})")

    @pytest.mark.parametrize(
        "text", [pytest.param("a|tex'q'", marks=NAMES), pytest.param("xs[0].tex'q'", marks=NAMES)]
    )
    def test_a_tex_string_after_a_bar_or_a_dot_is_an_error(self, text):
        syntax_error(f"(f {text})")

    @UNICODE_CONSTANTS
    def test_pi_written_as_a_greek_letter_is_no_name(self):
        compile_error("(real v π)")


@rule("name-underscore")
class TestNameUnderscore:
    @pytest.mark.parametrize(
        "src, head",
        [
            ("(circle_ (r 1))", name("circle")),
            ("(marks.grid_ a)", name("marks", "grid")),
        ],
    )
    def test_an_underscore_at_the_end_of_a_head(self, src, head):
        assert forms(src)[0].items[:2] == (head, NoneLit())

    def test_an_underscore_after_a_broadened_type_and_after_none(self):
        assert len(forms("(line|none_ (r 1))")[0].items) == 3
        assert forms("(none_ a)")[0].items == (NoneLit(), NoneLit(), name("a"))

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("x_", marks=NAMES),
            "a_b",
            "_x",
            "_",
            pytest.param("a_.b", marks=NAMES),
            pytest.param("a._", marks=NAMES),
            pytest.param("_.a", marks=NAMES),
            pytest.param("_[0]", marks=NAMES),
        ],
    )
    def test_an_underscore_in_any_other_place_is_an_error(self, text):
        syntax_error(f"(f {text})")


@rule("literal-words")
class TestLiteralWords:
    def test_bools_and_none(self):
        assert items("(f true false none)") == (BoolLit(True), BoolLit(False), NoneLit())

    @pytest.mark.parametrize("op", ["+", "-", "*", "/", "^", "<", "<=", ">", ">=", "=", "!=", "."])
    def test_each_operator_is_a_name_of_one_part(self, op):
        assert items(f"(f {op})") == (name(op),)

    @pytest.mark.parametrize(
        "src",
        [
            "(f +[0])",
            "(f true[0])",
            pytest.param("(f none[0])", marks=LITERAL_PARTS),
            "(f 3[0])",
            pytest.param("(f !=x)", marks=NAMES),
        ],
    )
    def test_brackets_after_an_operator_a_bool_none_or_a_number_are_errors(self, src):
        syntax_error(src)


KEYWORDS = (
    "import type interface namespace palette colormap scene formula motif variant func "
    "transition animation choreo "
    "circle rect ellipse line triangle polyline polygon curve arc ring text group row column "
    "let foreach exists-when term doc "
    "name if when cond else and or fn type-of as "
    "move wait roll-dice at-once in-order "
    "canvas readout display slider button play stepper toggle "
    "on-drag on-click on-release on-dragstart on-dragend on-enter on-leave on-pointermove "
    "on-show on-hide on-view on-ready on-live on-quiet"
).split()
# The keywords that today's compiler already forbids as the name of a variable.
FORBIDDEN_TODAY = {
    "scene", "animation", "transition", "move", "in-order", "at-once", "when", "else", "doc",
}  # fmt: skip

NOT_KEYWORDS = "x r size gap step fill duration like defaults loop const length wrap".split()


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


@rule("declaration-names")
class TestDeclarationNames:
    @pytest.mark.parametrize(
        "src",
        [
            pytest.param("(real if 1)", marks=KEYWORD_NAMES),
            pytest.param("(scene s (circle line (r 1)))", marks=KEYWORD_NAMES),
            "(func if ((real a)) a)",
            pytest.param("(func f ((real if)) if)", marks=KEYWORD_NAMES),
            pytest.param("(real v (let ((if 2)) if))", marks=KEYWORD_NAMES),
            pytest.param("(scene s (foreach if 2 (circle_ (r 1))))", marks=KEYWORD_NAMES),
            pytest.param("(namespace n (real if 1))", marks=KEYWORD_NAMES),
            pytest.param("(palette p (if 'red'))", marks=KEYWORD_NAMES),
            pytest.param("(formula if tex'x')", marks=KEYWORD_NAMES),
            pytest.param("(motif if () (circle_ (r 1)))", marks=KEYWORD_NAMES),
            pytest.param("(font if (size 12))", marks=KEYWORD_NAMES),
        ],
    )
    def test_no_declaration_of_any_kind_takes_a_keyword(self, src):
        compile_error(src)

    @pytest.mark.parametrize(
        "word",
        [
            pytest.param(t, marks=KEYWORD_NAMES)
            for t in [
                "int", "ratio", "real", "complex", "bool", "string", "color", "font", "point",
                "transform", "func", "list", "maybe", "shape", "positioned",
                "sequence",
            ]
        ],
    )  # fmt: skip
    def test_no_declaration_takes_a_built_in_type(self, word):
        compile_error(f"(real {word} 1)")

    def test_no_declaration_takes_the_type_of_seeds(self):
        compile_error("(real rand-seed 1)")

    @pytest.mark.parametrize("word", [pytest.param("pointer", marks=KEYWORD_NAMES), "self"])
    def test_no_declaration_takes_pointer_or_self(self, word):
        compile_error(f"(real {word} 1)")

    @KEYWORD_NAMES
    def test_self_in_a_let(self):
        compile_error("(real v (let ((self 2)) self))")

    def test_a_declaration_may_take_the_name_of_a_built_in_function(self):
        m = accepted("(func max ((real a) (real b)) a) (real v (max 1 2))")
        assert m.get("v").value.value == 1

    def test_a_declaration_may_take_the_name_of_an_operator(self):
        m = accepted("(func + ((real a) (real b)) 7) (real v (+ 1 2))")
        assert m.get("v").value.value == 7

    @pytest.mark.parametrize("constant", ["pi", "tau", "euler"])
    def test_a_declaration_may_take_the_name_of_a_built_in_constant(self, constant):
        m = accepted(f"(real {constant} 3) (real v {constant})")
        assert m.get("v").value.deps == {(m.id(constant), None)}

    @KEYWORD_NAMES
    def test_a_function_may_take_the_name_of_a_constant(self):
        m = accepted("(func pi ((real a)) a) (real v (pi 2))")
        assert m.get("v").value.value == 2


@rule("reserved-characters")
class TestReservedCharacters:
    @pytest.mark.parametrize(
        "src",
        [
            "(f {a})",
            "(f })",
            '(f "x")',
            "(f $x)",
            "(f #x)",
            pytest.param("(f :a)", marks=NAMES),
            "(f 'a':b)",
        ],
    )
    def test_reserved_characters_outside_strings_are_errors(self, src):
        syntax_error(src)

    def test_inside_a_string_they_are_text(self):
        assert items("(f '{a} \"b\" $c #d :e')") == (StrLit('{a} "b" $c #d :e'),)


@rule("number-literals")
class TestNumberLiterals:
    @pytest.mark.parametrize(
        "text, node",
        [
            ("3", IntLit(3)),
            ("007", IntLit(7)),
            ("+4", IntLit(4)),
            ("-12", IntLit(-12)),
            ("123456789012345678901234567890", IntLit(123456789012345678901234567890)),
            ("1/3", RatioLit(Fraction(1, 3))),
            ("-2/4", RatioLit(Fraction(-1, 2))),
            ("2.5", RealLit(2.5)),
            ("1.", RealLit(1.0)),
            (".5", RealLit(0.5)),
            ("1e3", RealLit(1000.0)),
            ("1.5E-3", RealLit(0.0015)),
            ("2i", ComplexLit(2j)),
            ("-1.5e3i", ComplexLit(-1500j)),
            ("1+2i", ComplexLit(1 + 2j)),
            ("-1e+2-3.5i", ComplexLit(-100 - 3.5j)),
        ],
    )
    def test_each_kind_of_number(self, text, node):
        (got,) = items(f"(f {text})")
        assert got == node
        assert type(got) is type(node)

    def test_a_real_is_the_nearest_double(self):
        (got,) = items("(f 0.1)")
        assert got.value == 0.1

    def test_each_part_of_a_complex_number_is_a_real(self):
        (got,) = items("(f 1+2i)")
        assert isinstance(got.value.real, float) and isinstance(got.value.imag, float)

    @pytest.mark.parametrize("src", ["(f 1/0)", "(f 1/-2)", "(f 1-2)", "(f 1e)", "(f 1/2/3)"])
    def test_not_numbers(self, src):
        syntax_error(src)

    @pytest.mark.parametrize(
        "text", [pytest.param("٣", marks=DIGITS), pytest.param("1/٣", marks=DIGITS), "²"]
    )
    def test_only_ascii_digits_are_digits(self, text):
        syntax_error(f"(f {text})")


@rule("string-literals")
class TestStringLiterals:
    def test_the_three_escapes(self):
        assert items("(f 'it\\'s' 'a\\\\b' 'a\\nb')") == (
            StrLit("it's"),
            StrLit("a\\b"),
            StrLit("a\nb"),
        )

    def test_a_line_feed_is_itself(self):
        assert items("(f 'a\nb')") == (StrLit("a\nb"),)

    def test_any_other_escape_is_an_error(self):
        syntax_error("(f 'a\\q')")

    def test_an_unclosed_string_is_an_error(self):
        syntax_error("(f 'a)")


@rule("tex-strings")
class TestTexStrings:
    def test_backslashes_stay_as_written(self):
        assert items("(f tex'\\frac12' tex'\\q')") == (
            StrLit("\\frac12", tex=True),
            StrLit("\\q", tex=True),
        )

    def test_an_escaped_quote_is_a_quote(self):
        assert items("(f tex'f\\'(x)')") == (StrLit("f'(x)", tex=True),)

    def test_a_backslash_and_the_next_character_are_read_together(self):
        assert items("(f tex'a\\\\')") == (StrLit("a\\\\", tex=True),)


@rule("prefix-forms")
class TestPrefixForms:
    def test_a_docstring(self):
        assert items("(f doc@'text')") == (form(name("doc"), StrLit("text")),)

    def test_a_free_starting_value(self):
        assert items("(f free@green)") == (form(name("free"), name("green")),)
        assert items("(f free@(g))") == (form(name("free"), form(name("g"))),)

    def test_an_optional_argument(self):
        assert items("(circle c r@1 fill@'red')") == (
            name("c"),
            form(name("r"), IntLit(1)),
            form(name("fill"), StrLit("red")),
        )

    @pytest.mark.parametrize(
        "src, written",
        [
            ("(f to@pointer.x)", "(f (to pointer.x))"),
            ("(f marks.grid@g)", "(f (marks.grid g))"),
            ("(f r@(* 2 k))", "(f (r (* 2 k)))"),
            ("(f pos@[1 2])", "(f (pos [1 2]))"),
            ("(f f@#'a-{k}')", "(f (f #'a-{k}'))"),
            ("(f x@xs[0] y@a|b)", "(f (x xs[0]) (y a|b))"),
            (
                "(f r@none s@true t@-1.5 u@tex'q' v@$'{k}')",
                "(f (r none) (s true) (t -1.5) (u tex'q') (v $'{k}'))",
            ),
            ("(f free@(g)x)", "(f (free (g)) x)"),
            ("(f $'{r@x:.2f}')", "(f $'{(r x):.2f}')"),
        ],
    )
    def test_it_is_the_form_of_the_head_and_the_item(self, src, written):
        assert items(src) == items(written)

    def test_the_form_and_its_head_have_the_position_of_its_first_character(self):
        (r,) = items("(f  r@1)")
        assert (r.pos.line, r.pos.col) == (1, 5)
        assert (r.items[0].pos.line, r.items[0].pos.col) == (1, 5)
        assert (r.items[1].pos.line, r.items[1].pos.col) == (1, 7)

    @pytest.mark.parametrize(
        "src",
        [
            "(f fill@free@green)",
            "(f r@a@b)",
            "(f +@1)",
            "(f .@1)",
            "(f circle_@c)",
            "(f none@1)",
            "(f true@1)",
            "(f 1@x)",
            "(f #'a'@1)",
            "(f #'a{b}'@1)",
            "(f xs[0]@1)",
            "(f a|r@1)",
            "(f r@ 1)",
            "(f r @1)",
            "(f doc@;c\n'x')",
            "(f r@)",
            "(f @x)",
            "(f a@b@)",
        ],
    )
    def test_nothing_between_the_prefix_and_its_item_and_no_other_at_sign(self, src):
        syntax_error(src)

    def test_the_form_must_be_allowed_where_it_is_written(self):
        compile_error("(bool c true) (real k if@c)")


@rule("interpolated-strings")
class TestInterpolatedStrings:
    def test_text_and_braces(self):
        assert items("(f $'a = {a}')") == (InterpStrLit(("a = ", name("a"))),)

    def test_doubled_braces_and_escapes(self):
        assert items("(f $'{{x}}\\'')") == (InterpStrLit(("{x}'",)),)

    def test_a_format_spec(self):
        assert items("(f $'{x:.2f}')") == (InterpStrLit((Field(name("x"), ".2f"),)),)

    def test_whitespace_around_the_expression(self):
        assert items("(f $'{ x }')") == items("(f $'{x}')")

    def test_a_comment_inside_a_form_in_the_braces(self):
        assert items("(f $'{(g ; c\n x)}')") == items("(f $'{(g x)}')")

    @BRACE_COMMENTS
    def test_a_comment_around_the_expression_is_an_error(self):
        syntax_error("(f $'{x ; c\n}')")

    def test_a_name_string(self):
        assert items("(f #'dot-{k}')") == (form(name("name"), InterpStrLit(("dot-", name("k")))),)

    @pytest.mark.parametrize(
        "src", ["(f $'}')", "(f $'a}b')", "(f #'plain')", "(f $'{}')", "(f $'{a b}')"]
    )
    def test_errors(self, src):
        syntax_error(src)

    def test_a_colon_in_a_nested_expression_is_an_error(self):
        syntax_error("(f $'{(g a:b)}')")

    @NESTED_BRACES
    def test_braces_are_read_the_same_at_every_depth(self):
        assert items("(f $'{$'{a}'}')") == (InterpStrLit((InterpStrLit((name("a"),)),)),)

    @NESTED_BRACES
    def test_after_a_nested_name_string_the_braces_go_on(self):
        (s,) = items("(f $'{#'n-{k}'.x:y}')")
        (field,) = s.parts
        assert isinstance(field, Field) and field.spec == "y"
        assert isinstance(field.expr, Form)
