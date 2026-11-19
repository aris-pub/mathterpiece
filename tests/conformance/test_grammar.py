"""Conformance tests for docs/spec/grammar.md."""

import pytest
from helpers import field, interp

from mathterpiece.nodes import (
    Bar,
    Brackets,
    ComplexLit,
    IntLit,
    ListLit,
    NoneLit,
    RatioLit,
    RealLit,
    StrLit,
)

from .support import (
    REJECTION,
    accepted,
    compile_error,
    form,
    forms,
    in_folder,
    items,
    mtpc,
    name,
    obj,
    rejected,
    syntax_error,
)

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


DOCSTRING_PLACE = xfail("mtp-ydd4.7.34", "the compiler takes a docstring from any place")
MOTIF_DOCSTRING = xfail("mtp-qiro", "a variable in a motif's body may not have a docstring")
OPTIONS_LAST = xfail("mtp-ydd4.7.11", "some forms allow a named argument after the body")
TOP_LET = xfail("mtp-ydd4.7.7", "a let at the top level is an error")
BODY_LET = xfail("mtp-ydd4.7.8", "a let is an error in some bodies that hold items")
ARGUMENT_LET = xfail("mtp-ydd4.7.9", "a let or a foreach among the arguments of a shape compiles")
GROUP_EXISTS_WHEN = xfail("mtp-ydd4.7.10", "a group keeps every exists-when until its end")
IMPORT_ORDER = xfail("mtp-ydd4.7.12", "every import is read before any other form")

D = name(".")


def dot(x, y):
    return form(D, x, y)


@rule("forms")
class TestForms:
    def test_the_items_of_a_form_are_expressions(self):
        assert forms("(circle c (r 1))") == (
            form(name("circle"), name("c"), form(name("r"), IntLit(1))),
        )

    @pytest.mark.parametrize(
        "src", ["(f [1 2])", "(f 'a')", "(f f'a{b}')", "(f real|none)", "(f 2.5)"]
    )
    def test_an_item_may_be_any_kind_of_expression(self, src):
        assert len(items(src)) == 1

    def test_the_empty_form_has_no_items(self):
        assert forms("(f ())") == (form(name("f"), form()),)


@rule("top-level-forms")
class TestTopLevelForms:
    @pytest.mark.parametrize("src", ["", "  ; only a comment\n", "(a)(b)", "\n(a)\n ; c\n(b)"])
    def test_any_number_of_forms(self, src):
        forms(src)

    @pytest.mark.parametrize("src", ["x", "'s'", "[1]", "(a)x", "1", "(a) )"])
    def test_anything_else_is_an_error(self, src):
        syntax_error(src)

    def test_a_source_with_no_form_compiles(self):
        accepted("")


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


@rule("lists")
class TestLists:
    def test_lists(self):
        assert items("(f [] [0 1] [(g x) 'a'])") == (
            ListLit(()),
            ListLit((IntLit(0), IntLit(1))),
            ListLit((form(name("g"), name("x")), StrLit("a"))),
        )

    def test_brackets_after_a_list(self):
        assert items("(f [a b c][h])") == (
            dot(ListLit((name("a"), name("b"), name("c"))), name("h")),
        )

    @pytest.mark.parametrize("src", ["(f [1][0 1])", "(f [1][])", "(f [1)"])
    def test_brackets_after_a_list_hold_exactly_one_expression(self, src):
        syntax_error(src)


@rule("name-brackets")
class TestNameBrackets:
    def test_one_expression(self):
        assert items("(f xs[0] xs[(+ k 1)] g['m1'])") == (
            name("xs", IntLit(0)),
            name("xs", form(name("+"), name("k"), IntLit(1))),
            name("g", StrLit("m1")),
        )

    def test_several_expressions(self):
        assert items("(f func[real real])") == (
            name("func", Brackets((name("real"), name("real")))),
        )

    def test_chains_of_brackets_and_parts(self):
        assert items("(f xs[0].pos.x m[0][1] a[0].b[1])") == (
            name("xs", IntLit(0), "pos", "x"),
            name("m", IntLit(0), IntLit(1)),
            name("a", IntLit(0), "b", IntLit(1)),
        )

    def test_a_bracket_after_whitespace_starts_a_list(self):
        assert items("(f xs [0])") == (name("xs"), ListLit((IntLit(0),)))

    @pytest.mark.parametrize("src", ["(f xs[])", "(f xs[0)", "(f xs[0].)"])
    def test_errors(self, src):
        syntax_error(src)


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


@rule("parser-expressions")
class TestParserExpressions:
    def test_one_expression_for_each_form_in_order(self):
        assert forms("(a) (b)") == (form(name("a")), form(name("b")))

    @pytest.mark.parametrize(
        "text, node",
        [
            ("(g x)", form(name("g"), name("x"))),
            ("[1]", ListLit((IntLit(1),))),
            ("p.pos.x", name("p", "pos", "x")),
            ("xs[0].y", name("xs", IntLit(0), "y")),
            ("xs[(f)]", name("xs", form(name("f")))),
            ("real|none", Bar((name("real"), NoneLit()))),
            ("'s'", StrLit("s")),
            ("$'s'", StrLit("s", tex=True)),
            ("f'a{x}'", interp(("a", name("x")))),
            ("f'{x:.2f}'", interp((field(name("x"), ".2f"),))),
            ("3", IntLit(3)),
            ("1/3", RatioLit(__import__("fractions").Fraction(1, 3))),
            ("2.5", RealLit(2.5)),
            ("1+2i", ComplexLit(1 + 2j)),
            ("none", NoneLit()),
        ],
    )
    def test_each_kind_of_expression(self, text, node):
        assert items(f"(f {text})") == (node,)

    def test_two_pieces_of_text_are_never_next_to_each_other(self):
        assert items("(f f'a{{b}}c')") == (interp(("a{b}c",)),)


@rule("parser-sugar")
class TestParserSugar:
    def test_docstring(self):
        assert items("(f doc@'text')") == (form(name("doc"), StrLit("text")),)

    def test_prefixed_form(self):
        assert items("(f r@1)") == (form(name("r"), IntLit(1)),)
        assert items("(f free@x)") == (form(name("free"), name("x")),)

    def test_name_string(self):
        n = form(name("name"), interp(("dot-", name("k"))))
        assert items("(f #'dot-{k}')") == (n,)
        assert items("(f #'dot-{k}'.a.b)") == (dot(dot(n, name("a")), name("b")),)
        assert items("(f #'dot-{k}'[i])") == (dot(n, name("i")),)

    def test_brackets_after_a_list(self):
        assert items("(f [a b c][h])") == (
            dot(ListLit((name("a"), name("b"), name("c"))), name("h")),
        )

    def test_the_position_of_the_form_is_its_first_character(self):
        (s,) = items("(f  doc@'x')")
        assert (s.pos.line, s.pos.col) == (1, 5)
        (s,) = items("(f  #'d-{k}'.a)")
        inner = s.items[1]
        assert (inner.pos.line, inner.pos.col) == (1, 5)

    def test_a_dot_form_after_a_name_string_has_the_position_of_its_dot(self):
        (s,) = items("(f #'d-{k}'.a[0])")
        assert (s.pos.line, s.pos.col) == (1, 14)
        assert (s.items[1].pos.line, s.items[1].pos.col) == (1, 12)


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


@rule("form-template")
class TestFormTemplate:
    @pytest.mark.parametrize(
        "src",
        [
            "(real k 1 (>= 0))",
            "(list[color] cs ['red' 'blue'])",
            "(func[real] f ((real x)) x)",
            "(real|none k none)",
            "((real (>= 0)) r 1)",
            "(scene s (circle c (r 1) (fill 'red')))",
        ],
    )
    def test_heads_of_each_kind(self, src):
        accepted(src)

    def test_a_form_head_gives_a_type(self):
        compile_error("((real (>= 0)) r -1)")


@rule("declared-names")
class TestDeclaredNames:
    def test_a_name_string(self):
        d = mtpc("(scene s (foreach i 2 (circle #'d-{i}' (r 1))))")
        assert {"d-0", "d-1"} <= set(d["names"])

    def test_the_name_form(self):
        d = mtpc("(scene s (circle (name 'c') (r 1)))")
        assert obj(d, "c")["kind"] == "circle"

    def test_none_means_no_name(self):
        d = mtpc("(scene s (circle none (r 1)))")
        assert [o for o in d["objects"] if o["kind"] == "circle"][0].get("name") is None

    def test_a_name_in_quotes_is_an_error(self):
        compile_error("(real 'k' 1)")

    def test_the_string_of_a_name_string_is_known_when_compiling(self):
        compile_error("(real j 1) (scene s (circle #'c-{j}' (r 1)))")


@rule("forms-with-no-name")
class TestFormsWithNoName:
    def test_the_second_item_of_a_move_is_its_target(self):
        accepted("(real k 0) (button b (animation (move k (to 1) (duration 1))))")

    def test_a_listener_has_no_name(self):
        accepted("(scene s (circle c (r 1))) (canvas v s (on-click c))")

    def test_a_view_always_has_a_name(self):
        compile_error("(scene s (circle c (r 1))) (canvas_ s)")

    def test_a_control_always_has_a_name(self):
        compile_error("(real k 0 (>= 0) (<= 1)) (slider_ (move k (from 0) (to 1)))")


@rule("named-arguments-first")
class TestOptionalArgumentsFirst:
    def test_in_any_order_before_the_body(self):
        assert mtpc("(scene s (circle c (r 1) (fill 'red')))") == mtpc(
            "(scene s (circle c (fill 'red') (r 1)))"
        )

    def test_an_optional_argument_after_the_body_is_an_error(self):
        compile_error("(scene s (circle c (r 1)) (background 'white'))")

    def test_like_comes_first(self):
        compile_error("(scene s (circle a (r 1)) (circle b (fill 'red') (like a)))")
        accepted("(scene s (circle a (r 1)) (circle b (like a) (fill 'red')))")

    @OPTIONS_LAST
    def test_the_defaults_of_a_formula(self):
        compile_error("(formula f $'\\term{a}{x}' (term a (fill 'red')) (defaults (padding 3)))")

    @OPTIONS_LAST
    def test_the_font_of_a_readout(self):
        compile_error("(font f (size 12)) (readout r 'x' (on-live (animation)) (font f))")

    @OPTIONS_LAST
    def test_the_kind_of_a_display(self):
        compile_error("(formula f $'x') (display d f (on-live (animation)) (kind 'block'))")


@rule("named-arguments-once")
class TestOptionalArgumentsOnce:
    def test_twice_is_an_error(self):
        compile_error("(scene s (circle c (fill 'red') (fill 'blue')))")

    def test_pos_and_x_give_x_twice(self):
        compile_error("(scene s (circle c (pos [1 2]) (x 3) (r 1)))")


@rule("docstrings")
class TestDocstrings:
    @pytest.mark.parametrize(
        "src",
        [
            "(real k 1 doc@'d' (>= 0))",
            "(func f ((real x)) doc@'d' (* 2 x))",
            "(scene s (circle c (r 1) doc@'d'))",
            "(scene s (circle c (r 1))) (canvas v s (on-click c doc@'d'))",
        ],
    )
    def test_after_the_arguments_and_before_the_body(self, src):
        accepted(src)

    @pytest.mark.parametrize(
        "src",
        [
            pytest.param("(real k 1 (>= 0) doc@'d')", marks=DOCSTRING_PLACE),
            pytest.param("(func f ((real x)) (* 2 x) doc@'d')", marks=DOCSTRING_PLACE),
            pytest.param("(scene s (circle c doc@'d' (r 1)))", marks=DOCSTRING_PLACE),
            pytest.param(
                "(real k 0) (button b doc@'d' (animation (move k (to 1) (duration 1))))",
                marks=DOCSTRING_PLACE,
            ),
        ],
    )
    def test_in_any_other_place_it_is_an_error(self, src):
        compile_error(src)

    def test_at_most_one(self):
        compile_error("(real k 1 doc@'a' doc@'b')")

    def test_an_interpolated_docstring_is_an_error(self):
        rejected("(real k 1 (doc f'd{k}'))")

    @MOTIF_DOCSTRING
    def test_a_variable_in_a_motif_body_may_have_one(self):
        accepted("(motif m () (real k 1 doc@'d') (circle c (r k)))")

    def test_the_docstring_is_kept(self):
        assert obj(mtpc("(real k 1 doc@'the radius')"), "k")["doc"] == "the radius"


@rule("contexts")
class TestContexts:
    @pytest.mark.parametrize(
        "src",
        [
            "(circle c (r 1))",
            "(scene s (circle c (r 1))) (on-click c)",
            "(formula f $'\\term{a}{x}') (term a (fill 'red'))",
            "(scene s (group g (real k 1) (circle c (r 1))))",
            "(scene s (motif m () (circle_ (r 1))))",
            "(scene s (circle c (r 1)) (canvas v s))",
            "(namespace n (func f ((real x)) x))",
            "(palette p (palette q ('a' 'red')))",
            "(variant v ((real k 1)) (circle (r k)) (circle (r k)))",
            "(func f ((real x)) x x)",
            "(scene s (group g (clip (line (from [0 0]) (to [1 1]))) (circle c (r 1))))",
            "(real k 0) (scene s (circle c (r 1))) (canvas v s (move k (to 1)))",
            "(real k 0) (motif m () (animation a (move k (to 1) (duration 1))) (circle_ (r 1)))",
        ],
    )
    def test_an_item_that_the_body_does_not_hold_is_an_error(self, src):
        rejected(src)

    def test_a_file_to_import_holds_only_what_it_may(self, tmp_path):
        with pytest.raises(REJECTION):
            in_folder(tmp_path, {"lib.mtp": "(real k 1)\n"}, "(import lib)\n(real v lib.k)\n")

    @pytest.mark.parametrize(
        "src",
        [
            "(scene s (real k 1 (>= 0)) (circle c (r k)))",
            "(scene s (group g (circle c (r 1)) (circle|none d (r 1)) (exists-when d true)))",
            "(motif m ((real k 1 (>= 0))) (circle_ (r k))) (scene s (m a))",
            "(namespace n (real k 1) (namespace m (real j 2)))",
            "(palette p (a 'red') (b 'blue'))",
            "(formula f $'\\term{a}{x}' (term a (fill 'red')))",
        ],
    )
    def test_items_that_the_body_holds(self, src):
        accepted(src)


@rule("body-let-foreach")
class TestBodyLetForeach:
    def test_a_foreach_at_the_top_level(self):
        d = mtpc("(foreach i 3 (real #'k-{i}' i))")
        assert {"k-0", "k-1", "k-2"} <= set(d["names"])

    @TOP_LET
    def test_a_let_at_the_top_level(self):
        accepted("(let ((k 2)) (real a k))")

    def test_a_let_in_the_scene(self):
        accepted("(scene s (let ((k 2)) (circle c (r k))))")

    @BODY_LET
    def test_a_let_in_an_animation(self):
        accepted("(real k 0) (animation a (let ((t 1)) (move k (to 1) (duration t))))")

    @BODY_LET
    def test_a_let_in_a_namespace(self):
        accepted("(namespace n (let ((t 1)) (real k t)))")

    @pytest.mark.parametrize(
        "src",
        [
            pytest.param("(scene s (circle c (let ((k 2)) (r k))))", marks=ARGUMENT_LET),
            pytest.param("(scene s (circle c (foreach i 1 (r 2))))", marks=ARGUMENT_LET),
        ],
    )
    def test_never_among_the_arguments_of_a_form(self, src):
        compile_error(src)

    def test_never_in_the_body_of_a_function(self):
        rejected("(func f ((real x)) (let ((k 2)) (real a k)))")

    @GROUP_EXISTS_WHEN
    def test_an_exists_when_names_a_shape_declared_before_it(self):
        compile_error("(scene s (group g (exists-when c true) (circle|none c (r 1))))")


@rule("formula-terms")
class TestFormulaTerms:
    def test_the_string_declares_its_terms(self):
        accepted("(formula f (defaults (padding 3)) $'\\term{a}{x}' (term a (fill 'red')))")

    def test_a_term_that_the_string_does_not_mark_is_an_error(self):
        compile_error("(formula f $'\\term{a}{x}' (term b (fill 'red')))")

    @OPTIONS_LAST
    def test_a_term_before_the_string_is_an_error(self):
        compile_error("(formula f (term a (fill 'red')) $'\\term{a}{x}')")


@rule("listeners-in-views")
class TestListenersInViews:
    def test_a_listener_at_the_top_level_is_an_error(self):
        compile_error("(scene s (circle c (r 1))) (on-click c)")

    def test_a_listener_is_heard_in_its_own_view(self):
        d = mtpc("(scene s (circle c (r 1))) (canvas v s (on-click c)) (canvas w s)")
        listener = next(o for o in d["objects"] if o["kind"] == "on-click")
        assert listener["in"] == [d["names"]["v"]]

    def test_a_listener_on_its_own_view_leaves_out_its_name(self):
        accepted(
            "(real k 0) (scene s) (canvas v s (on-view (animation (move k (to 1) (duration 1)))))"
        )

    def test_a_listener_has_no_in(self):
        compile_error("(scene s (circle c (r 1))) (canvas v s (on-click c (in v)))")


@rule("import-declares-names")
class TestImportDeclaresNames:
    def test_a_name_used_after_the_import(self, tmp_path):
        in_folder(
            tmp_path, {}, "(import colors)\n(scene s (circle c (fill colors.tab10-named.red)))\n"
        )

    @IMPORT_ORDER
    def test_a_name_used_before_the_import_is_an_error(self, tmp_path):
        with pytest.raises(REJECTION):
            in_folder(
                tmp_path,
                {},
                "(scene s (circle c (fill colors.tab10-named.red)))\n(import colors)\n",
            )


@rule("literals")
class TestLiterals:
    @pytest.mark.parametrize(
        "decl",
        [
            "(real w 2.5)",
            "(string w 'crimson')",
            "(bool w true)",
            "(real|none w none)",
            "(list[real] w [0 1])",
            "(list[list[real]] w [[1 2] [3 4]])",
        ],
    )
    def test_a_literal_writes_a_value(self, decl):
        assert accepted(decl).get("w").value.value is not None or "none" in decl
