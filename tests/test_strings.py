"""Strings (mtp-rry4, the author, 2026-11-18): $'…' is a TeX string literal, f'…' is syntactic
sugar for (concat PIECE…), each {X} in it (fmt X) and each {X:S} (fmt X 'S'), @'…' is
(name f'…'), and concat and fmt are core forms and keywords (docs/spec/grammar.md,
"shorthand-forms"; docs/spec/lexical.md, "tex-strings" and "interpolated-strings")."""

import re

import pytest
from helpers import doc, error, model, value

from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.nodes import Form, IntLit, Name, Pos, StrLit
from mathterpiece.parse import ParseError, parse


def n(*parts):
    return Name(tuple(parts))


def concat(*pieces):
    return Form((n("concat"), *pieces))


def fmt(x, spec=None):
    return Form((n("fmt"), x) if spec is None else (n("fmt"), x, StrLit(spec)))


def items(node):
    assert isinstance(node, Form)
    return node.items


def atom(text):
    (form,) = parse(f"(f {text})")
    return form.items[1]


class TestParse:
    def test_the_example_of_the_spec(self):
        assert atom("f'x = {x:.2f}!'") == concat(StrLit("x = "), fmt(n("x"), ".2f"), StrLit("!"))

    def test_empty(self):
        assert atom("f''") == concat()

    def test_text_only(self):
        assert atom("f'plain'") == concat(StrLit("plain"))

    def test_pieces_of_text_are_as_long_as_possible(self):
        assert atom(r"f'a{{b}}\'c{k}'") == concat(StrLit("a{b}'c"), fmt(n("k")))

    def test_braces_next_to_each_other(self):
        assert atom("f'{a}{b:>3}'") == concat(fmt(n("a")), fmt(n("b"), ">3"))

    def test_an_empty_spec_is_kept(self):
        assert atom("f'{a:}'") == concat(fmt(n("a"), ""))

    def test_nested(self):
        assert atom("f'{f'{a}'}'") == concat(fmt(concat(fmt(n("a")))))

    def test_name_string(self):
        assert atom("@'dot-{k}'") == Form((n("name"), concat(StrLit("dot-"), fmt(n("k")))))

    def test_name_string_with_parts(self):
        inner = Form((n("name"), concat(StrLit("dot-"), fmt(n("k")))))
        assert atom("@'dot-{k}'.a") == Form((n("."), inner, n("a")))
        assert atom("@'dot-{k}'[0]") == Form((n("."), inner, IntLit(0)))

    def test_tex_string(self):
        assert atom(r"$'\frac{a}{b}'") == StrLit(r"\frac{a}{b}", tex=True)

    def test_tex_string_escapes_only_the_quote(self):
        assert atom(r"$'it\'s \\'") == StrLit(r"it's \\", tex=True)

    def test_a_tex_string_is_not_a_form(self):
        assert isinstance(atom("$'{a}'"), StrLit)

    @pytest.mark.parametrize("text", ["tex'q'", "a|f'q'", "xs[0].f'q'"])
    def test_the_old_prefix_and_misplaced_prefixes(self, text):
        with pytest.raises(ParseError, match="a name holds only ASCII"):
            parse(f"(f {text})")

    def test_a_prefixed_form_of_each(self):
        (form,) = parse("(f r@f'{k}' r@$'q')")
        assert form.items[1] == Form((n("r"), concat(fmt(n("k")))))
        assert form.items[2] == Form((n("r"), StrLit("q", tex=True)))

    def test_dollar_needs_a_quote(self):
        with pytest.raises(ParseError, match="'\\$' must be followed by a quote"):
            parse("(f $x)")


class TestPositions:
    def test_each_piece_is_where_its_text_is(self):
        #                 1234567890123456789
        (form,) = parse("(f f'x = {x:.2f}!')")
        head, text, field, bang = items(form.items[1])
        assert form.items[1].pos == Pos(1, 4)
        assert head.pos == Pos(1, 4)
        assert text.pos == Pos(1, 6)
        assert field.pos == Pos(1, 10)
        assert [p.pos for p in items(field)] == [Pos(1, 10), Pos(1, 11), Pos(1, 13)]
        assert bang.pos == Pos(1, 17)

    def test_name_string(self):
        (form,) = parse("(f @'a{k}')")
        _, text = items(form.items[1])
        assert form.items[1].pos == Pos(1, 4) and text.pos == Pos(1, 4)
        assert items(text)[2].pos == Pos(1, 7)

    def test_a_compile_error_inside_braces(self):
        with pytest.raises(CompileError) as e:
            compile_source("(readout r f'a {(nope 1)}')")
        assert e.value.pos == Pos(1, 17)

    def test_a_bad_spec_points_at_the_spec(self):
        with pytest.raises(CompileError) as e:
            compile_source("(readout r f'a {true:.2f}')")
        assert e.value.pos == Pos(1, 22)

    def test_an_unknown_name(self):
        with pytest.raises(CompileError) as e:
            compile_source("(readout r f'{x}')")
        assert e.value.pos == Pos(1, 15)


# What {X} and {X:S} gave inside $'…' before mtp-rry4, for values known when compiling: each
# (value, spec, text), spec None for {X}. (fmt X S) must give the same.
TODAY = [
    ("3", None, "3"),
    ("3", ".2f", "3.00"),
    ("3", ">8", "       3"),
    ("3", ".1%", "300.0%"),
    ("3", "e", "3.000000e+00"),
    ("3", "+d", "+3"),
    ("3", "b", "11"),
    ("3", "05.1f", "003.0"),
    ("-7", "x", "-7"),
    ("1/3", None, "0.3333333333333333"),
    ("1/3", ".2f", "0.33"),
    ("1/3", ">8", "0.3333333333333333"),
    ("1/3", "^9.3", "  0.333  "),
    ("2.675", None, "2.675"),
    ("2.675", ".2f", "2.68"),
    ("2.675", ".3g", "2.68"),
    ("0.1", ".1%", "10.0%"),
    ("1e20", None, "1e+20"),
    ("1e20", ".2f", "100000000000000000000.00"),
    ("pi", "e", "3.141593e+00"),
    ("(/ 4 2)", None, "2.0"),
    ("(/ 4 2)", ".3g", "2"),
    ("[1 2]", None, "[1, 2]"),
    ("[1 2]", "", "[1, 2]"),
    ("[true false]", None, "[True, False]"),
    ("['a' 'b']", None, "['a', 'b']"),
    ("[none 1]", None, "[None, 1]"),
    ("true", None, "True"),
    ("false", "", "False"),
    ("'abc'", None, "abc"),
    ("'abc'", ">8", "     abc"),
    ("1+2i", None, "(1+2j)"),
    ("none", None, None),
    ("none", "", None),
]


class TestFmt:
    @pytest.mark.parametrize("x, spec, text", TODAY)
    def test_as_braces_gave(self, x, spec, text):
        written = f"(fmt {x})" if spec is None else f"(fmt {x} '{spec}')"
        assert value(f"(string|none v {written})") == text
        braces = f"{{{x}}}" if spec is None else f"{{{x}:{spec}}}"
        assert value(f"(string|none v f'{braces}')") == text

    def test_a_point(self):
        assert value("(point p [1 2] (const)) (string v (fmt p))") == "(1.0, 2.0)"

    @pytest.mark.parametrize(
        "x, spec, t",
        [
            ("3", "^9.3", "int"),
            ("1/3", "x", "ratio"),
            ("true", ".2f", "bool"),
            ("[1 2]", ".2f", "list[int]"),
            ("none", ".2f", "none"),
            ("'abc'", ".1%", "string"),
        ],
    )
    def test_a_spec_that_does_not_fit(self, x, spec, t):
        error(
            f"(string|none v (fmt {x} '{spec}'))", re.escape(f"'{spec}' is not a format for a {t}")
        )

    def test_the_spec_is_a_known_string(self):
        assert value("(string s '.1f' (const)) (string v (fmt 2 s))") == "2.0"

    def test_a_spec_known_only_while_drawing(self):
        error("(string s '.1f') (readout v (fmt 2 s))", "known when compiling")

    def test_a_spec_that_is_not_a_string(self):
        error("(string v (fmt 2 3))", "expected string, got int")

    @pytest.mark.parametrize("src", ["(fmt)", "(fmt 1 '' '')"])
    def test_one_or_two_arguments(self, src):
        error(f"(string v {src})", r"fmt takes a value and a format spec: \(fmt x '\.2f'\)")


# The .mtpc of each source, as $'…' compiled before mtp-rry4.
TODAY_BOUND = [
    (
        "(real x 1) (int k 2) (readout v {})",
        "f'a {x:.2f} b {k}!'",
        "(concat 'a ' (fmt x '.2f') ' b ' (fmt k) '!')",
        {
            "bound": [
                *["format", "string", "a ", [["read", "real", 0, None, None], ".2f"], " b "],
                *[[["read", "int", 1, None, None], ""], "!"],
            ],
            "deps": [[0, None], [1, None]],
            "type": "string",
        },
    ),
    (
        "(real|none x 1) (readout v (or? {} 'n'))",
        "f'{x}'",
        "(fmt x)",
        {
            "bound": [
                *["builtin", "string", "or?"],
                [
                    *["format", {"union": ["string", "none"]}],
                    [["read", {"union": ["real", "none"]}, 0, None, None], ""],
                ],
                ["lit", "string", "n"],
            ],
            "deps": [[0, None]],
            "type": "string",
        },
    ),
    (
        "(string s 'q') (readout v {})",
        "f'<{s}>'",
        "(concat '<' s '>')",
        {
            "bound": ["format", "string", "<", [["read", "string", 0, None, None], ""], ">"],
            "deps": [[0, None]],
            "type": "string",
        },
    ),
    (
        "(point p [1 2]) (readout v {})",
        "f'{p} {3:.1f}'",
        "(concat (fmt p) ' ' (fmt 3 '.1f'))",
        {
            "bound": ["format", "string", [["read", "point", 0, None, None], ""], " 3.0"],
            "deps": [[0, None]],
            "type": "string",
        },
    ),
    (
        "(real x 1) (readout v {})",
        "f'{f'{x}'}'",
        "(fmt (fmt x))",
        {
            "bound": [
                *["format", "string"],
                [["format", "string", [["read", "real", 0, None, None], ""]], ""],
            ],
            "deps": [[0, None]],
            "type": "string",
        },
    ),
]


def readout_value(src):
    d = doc(src)
    (o,) = [o for o in d["objects"] if o.get("name") == "v"]
    return o["attrs"]["value"]


class TestTheMtpc:
    @pytest.mark.parametrize("template, sugar, forms, want", TODAY_BOUND)
    def test_as_interpolation_compiled(self, template, sugar, forms, want):
        assert readout_value(template.format(sugar)) == want
        assert readout_value(template.format(forms)) == want


class TestConcat:
    def test_joins(self):
        assert value("(string v (concat 'a' 'b' 'c'))") == "abc"

    def test_none(self):
        assert value("(string v (concat))") == ""

    def test_one(self):
        assert value("(string v (concat 'a'))") == "a"

    def test_strings_known_when_compiling(self):
        assert value("(string s 'b' (const)) (string v (concat 'a' s (concat 'c' 'd')))") == "abcd"

    def test_a_tex_string(self):
        assert value("(string v (concat $'\\alpha' ' and b'))") == "\\alpha and b"

    def test_none_gives_none(self):
        assert value("(string|none v (concat 'a' none))") is None
        assert value("(string|none v (concat 'a' (fmt none)))") is None

    @pytest.mark.parametrize("x, t", [("1", "int"), ("true", "bool"), ("[1 2]", "list[int]")])
    def test_an_argument_that_is_not_a_string(self, x, t):
        error(f"(string v (concat 'a' {x}))", re.escape(f"concat joins strings, got {t}"))

    def test_plus_stays_arithmetic(self):
        error("(string v (+ 'a' 'b'))", "takes numbers, got string")


MOVE = "(real k 0) (button b (animation (move k (to 1) (duration 1))) {})"


def button(label):
    d = doc(MOVE.format(label))
    (b,) = [o for o in d["objects"] if o.get("name") == "b"]
    return b


class TestTex:
    """There is no (tex …) form (the author, 2026-11-18): a TeX string $'…' is LaTeX in a label,
    and a formula's string and a term's string are LaTeX by their place."""

    def test_a_tex_string_is_a_string_elsewhere(self):
        assert value("(string v $'\\frac{a}{b}')") == "\\frac{a}{b}"
        error("(color v $'red')", "expected color, got string")

    def test_tex_is_no_form(self):
        error("(string v (tex 'a'))", "unknown function 'tex'")

    def test_tex_is_no_keyword(self):
        assert value("(real tex 1 (const)) (real v tex)") == 1

    def test_a_label_written_as_a_tex_string(self):
        b = button("(label $'C_{3}')")
        assert b["attrs"]["label"] == {"type": "string", "free": "C_{3}"}
        assert b["label-tex"] is True

    @pytest.mark.parametrize(
        "label", ["(label 'C_3')", "(label f'C_{1}')", "(label (concat $'C'))"]
    )
    def test_any_other_label_is_plain(self, label):
        assert "label-tex" not in button(label)

    def test_a_terms_string(self):
        m = model(r"(real q 0.3) (formula f $'p = \term{v}{}' (term v f'{q:.2f}'))")
        assert m.get("f.v").attrs["tex"].deps == {(m.id("q"), None)}

    @pytest.mark.parametrize("text", ["'x'", "$'\\alpha'", "(if true 'x' 'y')", "s"])
    def test_any_string_expression_in_a_term(self, text):
        m = model(
            f"(string s 'x' (const)) (formula f $'\\term{{v}}{{}}' (term v (fill #'red') {text}))"
        )
        assert m.get("f.v").attrs["tex"].value in ("x", "\\alpha")

    def test_a_term_holds_one_string(self):
        error(
            r"(formula f $'\term{v}{}' (term v 'a' (fill #'red') 'b'))",
            "a term holds one string, its LaTeX",
        )

    def test_like_copies_the_string(self):
        m = model(
            r"(formula f $'\term{a}{} \term{b}{}' (term a 'x' (fill #'red')) (term b (like a)))"
        )
        assert m.get("f.b").attrs["tex"].value == "x"

    def test_the_old_form_in_a_term(self):
        error(r"(formula f $'\term{v}{}' (term v (tex 'a')))", "a term has no attribute 'tex'")


class TestKeywords:
    @pytest.mark.parametrize("word", ["concat", "fmt"])
    @pytest.mark.parametrize(
        "template",
        [
            "(real {} 1)",
            "(func {} ((real x)) x)",
            "(func f ((real {})) 1)",
            "(real v (let (({} 1)) 2))",
            "(scene s (foreach {} 3 (circle_ (r 1))))",
            "(namespace n (real {} 1))",
            "(scene s (circle {} (r 1)))",
        ],
    )
    def test_no_declaration_or_binding_takes_one(self, word, template):
        with pytest.raises(CompileError):
            compile_source(template.format(word))
