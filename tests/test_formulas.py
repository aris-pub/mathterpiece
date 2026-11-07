"""Formulas (mtp-bz6h). The author, 2026-11-06: interactive typeset math, parallel to the scene's
interactive geometry. (formula name tex'…') is a top-level declaration beside the scene, its
LaTeX fixed when compiling, with terms marked \\term{name}{…}. Each term is an object,
formula.name, whose attributes (term name …) gives: its color, opacity and existence, the
adornments drawn around it without moving the glyphs, and its content as an expression, which
is how values enter a formula. A formula may declare variables of its own. Formulas and scenes
never read each other: they share only globals. A display shows one formula, inline or as a
block, and on-click, on-enter and on-leave listen to its terms."""

import pytest
from helpers import doc, error, model

BOUNDS = (
    r"(formula bounds tex'\term{gap}{\Big(1-\frac1b\Big)^2} P_h(p) \mathrel{\term{lo}{\le}}"
    r" \frac{a}{b} \mathrel{\term{hi}{\le}} P_h(p) + \term{b2}{\frac1{b^2}}')"
)


def obj(src, name):
    return model(src).get(name)


class TestDeclaring:
    def test_a_formula_keeps_its_latex(self):
        f = obj(BOUNDS, "bounds")
        assert f.kind == "formula"
        assert f.data["tex"].startswith(r"\term{gap}{\Big(1-\frac1b\Big)^2}")

    def test_each_marked_term_is_an_object(self):
        m = model(BOUNDS)
        assert [m.objects[i].name for i in m.get("bounds").members] == [
            "bounds.gap",
            "bounds.lo",
            "bounds.hi",
            "bounds.b2",
        ]
        assert m.get("bounds.gap").kind == "term"

    def test_a_term_with_no_form_has_the_defaults(self):
        a = obj(BOUNDS, "bounds.lo").attrs
        assert (a["fill"].value, a["opacity"].value, a["exists"].value) == (None, 1, True)
        assert (a["background"].value, a["outline"].value, a["padding"].value) == (None, None, 0)
        assert (a["outline-width"].value, a["rounding"].value) == (1, 0)

    def test_a_terms_attributes(self):
        src = BOUNDS[:-1] + " (term gap (fill 'teal') (opacity 0.4) (padding 2) (rounding 3)))"
        a = obj(src, "bounds.gap").attrs
        assert (a["fill"].value, a["opacity"].value) == ("#008080ff", 0.4)
        assert (a["padding"].value, a["rounding"].value) == (2, 3)

    def test_terms_nest(self):
        m = model(r"(formula f tex'\term{all}{\frac{\term{top}{a}}{b}}')")
        assert [m.objects[i].name for i in m.get("f").members] == ["f.all", "f.top"]

    def test_a_term_may_be_empty(self):
        assert obj(r"(formula f tex'x = \term{v}{}')", "f.v").kind == "term"

    def test_a_doc(self):
        assert obj("(formula f doc@'A sum.' tex'a+b')", "f").data["doc"] == "A sum."


class TestDeclaringErrors:
    def test_it_needs_a_name(self):
        error("(formula_ tex'a')", "a formula needs a name")

    def test_it_holds_latex(self):
        error("(formula f)", r"a formula holds its LaTeX: \(formula name tex'…'\)")

    def test_only_one_latex(self):
        error("(formula f tex'a' tex'b')", "a formula holds one LaTeX string")

    def test_the_latex_is_known_when_compiling(self):
        error("(real k 1) (formula f $'{k}')", "a formula's LaTeX is known when compiling")

    def test_a_term_form_names_a_marked_term(self):
        error(
            r"(formula f tex'\term{a}{x}' (term b (opacity 0.5)))",
            r"f has no term 'b': mark one in its LaTeX, \\term\{b\}\{…\}",
        )

    def test_a_term_is_marked_once(self):
        error(r"(formula f tex'\term{a}{x} + \term{a}{y}')", "the term 'a' is marked twice")

    def test_a_terms_form_is_given_once(self):
        error(
            r"(formula f tex'\term{a}{x}' (term a (opacity 0.5)) (term a (fill 'red')))",
            "the term 'a' is given twice",
        )

    def test_a_terms_name_is_a_name(self):
        error(r"(formula f tex'\term{a b}{x}')", r"'a b' is not a term's name")

    def test_braces_match(self):
        error(r"(formula f tex'\frac{a}{b')", "the formula's LaTeX has a '{' that is never closed")
        error(r"(formula f tex'a}')", r"the formula's LaTeX has a '}' that closes nothing")

    def test_escaped_braces_are_not_counted(self):
        assert obj(r"(formula f tex'\{a\}')", "f").kind == "formula"

    def test_no_shapes(self):
        error("(formula f tex'a' (circle c))", "a formula holds its LaTeX, terms and variables")

    def test_only_at_the_top_level(self):
        error("(scene s (formula f tex'a'))", "a formula is declared only at the top level")

    def test_a_term_takes_no_shape_attribute(self):
        error(
            r"(formula f tex'\term{a}{x}' (term a (stroke 'red')))",
            "a term has no attribute 'stroke'",
        )


class TestContent:
    def test_a_terms_content_follows_an_expression(self):
        m = model(r"(real q 0.3) (formula f tex'p = \term{v}{}' (term v (tex $'{q:.2f}')))")
        assert m.get("f.v").attrs["tex"].deps == {(m.id("q"), None)}

    def test_without_one_a_term_keeps_its_latex(self):
        assert "tex" not in obj(r"(formula f tex'\term{v}{x}')", "f.v").attrs


class TestExistence:
    def test_exists_when(self):
        m = model(r"(bool shown false) (formula f tex'\term{a}{x}' (exists-when a shown))")
        assert m.get("f.a").attrs["exists"].deps == {(m.id("shown"), None)}

    def test_exists_when_names_a_term(self):
        error(
            r"(bool shown false) (formula f tex'\term{a}{x}' (exists-when b shown))",
            "f has no term 'b'",
        )


class TestVariables:
    def test_a_formulas_own_variable(self):
        m = model(
            r"(formula f (bool lit false) tex'\term{a}{x}' (term a (opacity (if lit 1 0.4))))"
        )
        assert m.get("f.a").attrs["opacity"].deps == {(m.id("f.lit"), None)}

    def test_a_writer_writes_it_by_its_full_name(self):
        m = model(
            r"(formula f (bool lit false) tex'\term{a}{x}')"
            r" (display d f) (on-click f.a (animation (move f.lit (to true) (duration 0.2))))"
        )
        assert m.get("f.lit").kind == "variable"

    def test_only_the_formula_reads_it_by_its_bare_name(self):
        error("(formula f (bool lit false) tex'a') (bool v lit)", "unknown name 'lit'")


class TestReading:
    # The author, 2026-11-06: formulas and scenes never read each other; they share only globals.
    def test_a_formula_reads_globals(self):
        m = model(r"(real k 0.5 (>= 0) (<= 1)) (formula f tex'\term{a}{x}' (term a (opacity k)))")
        assert m.get("f.a").attrs["opacity"].deps == {(m.id("k"), None)}

    def test_a_formula_cannot_read_the_scene(self):
        error(
            r"(scene s (real k 0.5)) (formula f tex'\term{a}{x}' (term a (opacity k)))",
            "a formula cannot read k: it belongs to the scene",
        )

    def test_nor_a_shape(self):
        error(
            r"(scene s (circle c (r 0.5))) (formula f tex'\term{a}{x}' (term a (opacity c.r)))",
            "a formula cannot read c: it belongs to the scene",
        )

    def test_the_scene_cannot_read_a_formula(self):
        error(
            r"(formula f (real k 0.5) tex'\term{a}{x}') (scene s (circle c (r f.k)))",
            "the scene cannot read f.k: it belongs to the formula f",
        )

    def test_nor_a_terms_attribute(self):
        error(
            r"(formula f tex'\term{a}{x}') (scene s (circle c (r f.a.opacity)))",
            "the scene cannot read f.a: it belongs to the formula f",
        )

    def test_one_formula_cannot_read_another(self):
        error(
            r"(formula f (real k 0.5) tex'a') (formula g tex'\term{a}{x}' (term a (opacity f.k)))",
            "a formula cannot read f.k: it belongs to the formula f",
        )

    def test_a_formula_cannot_read_a_component(self):
        error(
            r"(real k 0) (slider s (move k (from 0) (to 1)))"
            r" (formula f tex'\term{a}{x}' (term a (opacity s.position)))",
            "a formula cannot read s: it has page access",
        )

    def test_components_read_both(self):
        m = model(
            r"(scene sc (real k 0.5)) (formula f (real j 1) tex'a')"
            r" (readout r $'{k} {f.j}')"
        )
        assert m.get("r").attrs["value"].deps == {(m.id("k"), None), (m.id("f.j"), None)}


class TestDefaultsAndLike:
    # mtp-mca1: a formula's (defaults …) give every term those attributes, and a term's own win;
    # (like t) copies an earlier term's arguments, and its own win.
    AB = r"tex'\term{a}{x} + \term{b}{y}'"

    def test_defaults_reach_every_term(self):
        m = model(
            f"(formula f (defaults (padding 3) (rounding 4)) {self.AB} (term a (fill 'red')))"
        )
        assert m.get("f.a").attrs["padding"].value == 3
        assert m.get("f.b").attrs["rounding"].value == 4

    def test_a_terms_own_wins(self):
        m = model(f"(formula f (defaults (padding 3)) {self.AB} (term a (padding 1)))")
        assert m.get("f.a").attrs["padding"].value == 1
        assert m.get("f.b").attrs["padding"].value == 3

    def test_each_term_has_its_own(self):
        m = model(f"(formula f (defaults (padding 3)) {self.AB})")
        assert m.get("f.a").attrs["padding"] is not m.get("f.b").attrs["padding"]

    def test_defaults_are_term_attributes(self):
        error(f"(formula f (defaults (tex 'z')) {self.AB})", "a formula's defaults are")
        error(f"(formula f (defaults (r 1)) {self.AB})", "a formula's defaults are")

    def test_defaults_once(self):
        error(f"(formula f (defaults (padding 1)) (defaults (padding 2)) {self.AB})", "twice")

    def test_like_copies_an_earlier_term(self):
        m = model(
            f"(formula f {self.AB} (term a (fill 'red') (padding 2))"
            " (term b (like a) (fill 'blue')))"
        )
        b = m.get("f.b").attrs
        assert b["padding"].value == 2 and b["fill"].value == "#0000ffff"

    def test_like_names_a_term_given_before(self):
        error(f"(formula f {self.AB} (term b (like a)) (term a (padding 2)))", "given before")


class TestDisplay:
    def test_a_display_shows_a_formula_as_a_block(self):
        d = obj(BOUNDS + " (display eq bounds)", "eq")
        assert (d.kind, d.data["formula"], d.data["as"]) == ("display", 0, "block")

    def test_inline(self):
        assert obj(BOUNDS + " (display eq bounds (kind 'inline'))", "eq").data["as"] == "inline"

    def test_it_needs_a_formula(self):
        error("(display eq)", r"a display shows a formula: \(display name formula\)")
        error("(real k 1) (display eq k)", "expected the name of a formula")

    def test_kind_is_inline_or_block(self):
        error(BOUNDS + " (display eq bounds (kind 'big'))", "'big' is not one of 'inline', 'block'")

    def test_kind_is_known_when_compiling(self):
        error(
            "(string w 'inline') " + BOUNDS + " (display eq bounds (kind w))",
            "a display's kind is known when compiling",
        )


class TestListeners:
    @pytest.mark.parametrize("head", ["on-click", "on-enter", "on-leave"])
    def test_a_term_takes_a_listener(self, head):
        m = model(
            "(string shown '') " + BOUNDS + " (display eq bounds)"
            f" ({head} bounds.gap (animation (move shown (to 'gap') (duration 0.2))))"
        )
        listener = next(o for o in m.objects if o.kind == head)
        assert listener.data["shape"] == m.id("bounds.gap")

    @pytest.mark.parametrize("head", ["on-release", "on-dragend"])
    def test_only_click_and_hover(self, head):
        error(
            "(string shown '') "
            + BOUNDS
            + f" ({head} bounds.gap (animation (move shown (to 'gap') (duration 0.2))))",
            "a term takes on-click, on-enter and on-leave",
        )

    def test_a_drag_is_not_on_a_term(self):
        error(
            "(real k 0) " + BOUNDS + " (on-drag bounds.gap k)",
            "a term takes on-click, on-enter and on-leave",
        )

    def test_a_writer_moves_a_terms_attribute(self):
        m = model(
            BOUNDS[:-1] + " (term gap (background none)))"
            " (on-enter bounds.gap"
            " (animation (move bounds.gap.background (to 'gold') (duration 0.2))))"
        )
        assert m.get("bounds.gap").attrs["background"].value is None

    def test_a_bound_attribute_is_not_written(self):
        error(
            "(real k 1 (>= 0) (<= 1)) " + BOUNDS[:-1] + " (term gap (opacity k)))"
            " (on-enter bounds.gap (animation (move bounds.gap.opacity (to 0.5) (duration 0.2))))",
            "bounds.gap.opacity is bound",
        )


class TestCompiledModel:
    def test_a_formula_and_its_terms(self):
        d = doc(BOUNDS[:-1] + " (term gap (fill 'teal')))" + " (display eq bounds (kind 'inline'))")
        kinds = {o["name"]: o for o in d["objects"]}
        f = kinds["bounds"]
        assert f["kind"] == "formula" and f["tex"].startswith(r"\term{gap}")
        assert [d["objects"][i]["name"] for i in f["members"]] == [
            "bounds.gap",
            "bounds.lo",
            "bounds.hi",
            "bounds.b2",
        ]
        term = kinds["bounds.gap"]
        assert term["kind"] == "term" and term["term"] == "gap"
        assert term["attrs"]["fill"]["free"] == "#008080ff"
        eq = kinds["eq"]
        assert (eq["kind"], eq["formula"], eq["as"]) == ("display", d["objects"].index(f), "inline")

    def test_a_range_a_term_cannot_prove(self):
        error(
            r"(real k 0.5) (formula f tex'\term{a}{x}' (term a (opacity k)))",
            r"f.a's opacity may break \(>= 0\): constrain what it reads so this can be proved$",
        )


def test_the_compiled_model_fits_the_schema():
    import json

    from mtpc_check import errors

    from mathterpiece.compiler import compile_source
    from mathterpiece.mtpc import write

    src = (
        "(string shown '') (real q 0.3 (>= 0) (<= 1)) "
        + BOUNDS[:-1]
        + " (bool lit false) (term gap (fill 'teal') (tex $'{q:.2f}')) (exists-when lo lit))"
        " (display eq bounds (kind 'inline'))"
        " (on-click bounds.gap (animation (move shown (to 'gap') (duration 0.2))))"
    )
    assert errors(json.loads(write(compile_source(src)))) == []
