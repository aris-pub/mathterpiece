"""Every listener is written inside the body of the view it acts in (mtp-6k7f), and belongs to that
view alone: a listener on a shape or a term hears the pointer only there. Controls stay at the top
level and name the views they belong to with (in view…) (mtp-2juu.1), to none without one, which
quiet mode (mtp-16z) reads."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors

SCENE = "(real k 0) (scene s (circle c) (rect r))"
GO = "(animation (move k (to 1) (duration 1)))"
FORMULA = r"(formula f tex'\term{t}{x} + \term{all}{\term{top}{a}}')"


def one(m, kind):
    (o,) = [o for o in m.objects if o.kind == kind]
    return o


def two_canvases(a="", b=""):
    return f"{SCENE} (canvas a s {a}) (canvas b s {b})"


ON_SHAPES = [
    ("on-drag", "(on-drag c c.pos)"),
    ("on-click", f"(on-click c {GO})"),
    ("on-release", f"(on-release c {GO})"),
    ("on-dragstart", f"(on-dragstart c {GO})"),
    ("on-dragend", f"(on-dragend c {GO})"),
    ("on-enter", f"(on-enter c {GO})"),
    ("on-leave", f"(on-leave c {GO})"),
    ("on-pointermove", "(on-pointermove c p)"),  # last: only a canvas takes it
]
ON_CANVAS = [
    ("on-view", f"(on-view {GO})"),
    ("on-live", f"(on-live {GO})"),
    ("on-quiet", f"(on-live {GO}) (on-quiet {GO})"),
    ("on-pointermove", "(on-pointermove p)"),
]
ON_TERMS = [
    ("on-click", f"(on-click f.t {GO})"),
    ("on-enter", f"(on-enter f.t {GO})"),
    ("on-leave", f"(on-leave f.t {GO})"),
]


class TestCanvas:
    @pytest.mark.parametrize("kind,src", ON_SHAPES)
    def test_a_listener_on_a_shape_belongs_to_its_canvas(self, kind, src):
        m = model(f"(point p) {two_canvases(b=src)}")
        o = one(m, kind)
        assert o.data["in"] == [m.id("b")] and o.data["shape"] == m.id("c")

    @pytest.mark.parametrize("kind,src", ON_CANVAS)
    def test_a_listener_on_the_canvas_names_no_view(self, kind, src):
        m = model(f"(point p) {two_canvases(b=src)}")
        o = next(o for o in m.objects if o.kind == kind)
        assert o.data["view"] == m.id("b") and o.data.get("in") is None

    def test_a_canvas_on_pointermove_has_no_shape(self):
        m = model(f"(point p) {two_canvases(a='(on-pointermove p)')}")
        assert one(m, "on-pointermove").data["shape"] is None

    def test_a_shape_heard_in_two_canvases_has_a_listener_in_each(self):
        m = model(two_canvases(f"(on-click c {GO})", f"(on-click c {GO})"))
        clicks = [o for o in m.objects if o.kind == "on-click"]
        assert [o.data["in"] for o in clicks] == [[m.id("a")], [m.id("b")]]

    def test_listeners_come_after_the_options_among_what_it_shows(self):
        m = model(f"{SCENE} (canvas a (pan false) c (on-click c {GO}) r (on-click r {GO}))")
        assert m.get("a").data["shows"] == [m.id("c"), m.id("r")]
        assert len([o for o in m.objects if o.kind == "on-click"]) == 2

    def test_an_option_after_a_listener(self):
        error(
            f"{SCENE} (canvas a s (on-click c {GO}) (pan false))",
            r"\(pan …\) is an optional argument, so it comes before the canvas's body",
        )

    def test_it_keeps_its_options_and_conditions(self):
        m = model(f"{SCENE} (canvas a s (on-drag c c.pos (active true) (<= c.x 5)))")
        d = one(m, "on-drag")
        assert d.data["in"] == [m.id("a")] and len(d.data["conditions"]) == 1
        assert d.data["active"] is not None

    def test_in_a_foreach(self):
        m = model(
            "(scene s (group g (foreach i 3 (circle #'d-{i}'))))"
            " (canvas a s (foreach d g (on-drag d d.pos)))"
        )
        drags = [o for o in m.objects if o.kind == "on-drag"]
        assert [o.data["shape"] for o in drags] == [m.id(f"d-{i}") for i in range(3)]
        assert all(o.data["in"] == [m.id("a")] for o in drags)

    def test_in_a_let(self):
        m = model(f"{SCENE} (canvas a s (let ((t 2)) (on-drag c c.pos (<= c.x t))))")
        assert one(m, "on-drag").data["in"] == [m.id("a")]

    def test_in_a_foreach_around_the_canvas(self):
        m = model(f"{SCENE} (foreach i 2 (canvas #'v-{{i}}' s (on-click c {GO})))")
        clicks = [o for o in m.objects if o.kind == "on-click"]
        assert [o.data["in"] for o in clicks] == [[m.id("v-0")], [m.id("v-1")]]

    def test_a_doc(self):
        m = model(f"{SCENE} (canvas a s (on-click c {GO} doc@'Grows k.'))")
        assert one(m, "on-click").data["doc"] == "Grows k."
        assert "doc" not in m.get("a").data

    def test_on_bubbles_up_to_a_group_it_shows(self):
        m = model(f"(real k 0) (scene s (group g (circle c))) (canvas a g (on-click c {GO}))")
        assert one(m, "on-click").data["in"] == [m.id("a")]

    def test_a_shape_shown_by_an_expression(self):
        m = model(f"(bool on) {SCENE} (canvas a r (when on c) (on-click c {GO}))")
        assert one(m, "on-click").data["in"] == [m.id("a")]

    @pytest.mark.parametrize("kind,src", ON_SHAPES + ON_CANVAS)
    def test_it_is_written(self, kind, src):
        d = doc(f"(point p) {two_canvases(b=src)}")
        o = next(o for o in d["objects"] if o["kind"] == kind)
        b = d["names"]["b"]
        assert o.get("in") == [b] or o.get("view") == b
        assert errors(d) == []


class TestDisplay:
    @pytest.mark.parametrize("kind,src", ON_TERMS)
    def test_a_listener_on_a_term_belongs_to_its_display(self, kind, src):
        m = model(f"(real k 0) {FORMULA} (display d f {src}) (display e f)")
        o = one(m, kind)
        assert o.data["in"] == [m.id("d")] and o.data["shape"] == m.id("f.t")

    def test_a_nested_term(self):
        m = model(f"(real k 0) {FORMULA} (display d f (on-enter f.top {GO}))")
        assert one(m, "on-enter").data["in"] == [m.id("d")]

    def test_after_its_kind(self):
        m = model(f"(real k 0) {FORMULA} (display d f (kind 'inline') (on-click f.t {GO}))")
        assert m.get("d").data["as"] == "inline"
        assert one(m, "on-click").data["in"] == [m.id("d")]

    @pytest.mark.parametrize("kind", ["on-live", "on-quiet"])
    def test_its_own_on_live_and_on_quiet(self, kind):
        m = model(f"(real k 0) {FORMULA} (display d f (on-live {GO}) (on-quiet {GO}))")
        assert one(m, kind).data["view"] == m.id("d")

    @pytest.mark.parametrize("kind,src", ON_TERMS)
    def test_it_is_written(self, kind, src):
        d = doc(f"(real k 0) {FORMULA} (display d f {src})")
        o = next(o for o in d["objects"] if o["kind"] == kind)
        assert o["in"] == [d["names"]["d"]]
        assert errors(d) == []


class TestReadout:
    @pytest.mark.parametrize("kind", ["on-live", "on-quiet"])
    def test_its_own_on_live_and_on_quiet(self, kind):
        m = model(f"(real k 0) (readout ro 'x' (on-live {GO}) (on-quiet {GO}))")
        assert one(m, kind).data["view"] == m.id("ro")

    def test_after_its_value(self):
        m = model(f"(real k 0) (readout ro $'{{k}}' (on-live {GO}))")
        assert one(m, "on-live").data["view"] == m.id("ro")


class TestErrors:
    @pytest.mark.parametrize("kind,src", ON_SHAPES)
    def test_a_listener_on_a_shape_at_the_top_level(self, kind, src):
        error(
            f"(point p) {SCENE} (canvas a s) {src}",
            rf"{kind} is written inside the body of the view it acts in: \(canvas name …"
            rf" \({kind} c",
        )

    def test_a_listener_on_a_term_at_the_top_level(self):
        error(
            f"(real k 0) {FORMULA} (display d f) (on-click f.t {GO})",
            r"on-click is written inside the body of the view it acts in: \(display name"
            r" formula … \(on-click f.t …\)\)",
        )

    @pytest.mark.parametrize("kind", ["on-view", "on-live", "on-quiet"])
    def test_a_listener_on_a_view_at_the_top_level(self, kind):
        error(
            f"{SCENE} (canvas a s) ({kind} a {GO})",
            rf"{kind} is written inside the body of the view it acts in: \(canvas a …"
            rf" \({kind} …\)\)",
        )

    def test_on_pointermove_on_a_canvas_at_the_top_level(self):
        error(
            f"(point p) {SCENE} (canvas a s) (on-pointermove a p)",
            r"on-pointermove is written inside the body of the view it acts in: \(canvas a …"
            r" \(on-pointermove p …\)\)",
        )

    def test_with_in_at_the_top_level(self):
        error(
            f"{two_canvases()} (on-click c (in a b) {GO})",
            r"a listener takes no \(in …\): it hears only in the view it is written in, so write"
            r" it inside the body of each view: \(canvas a … \(on-click c …\)\)",
        )

    def test_with_in_inside_a_view(self):
        error(
            two_canvases(f"(on-click c (in b) {GO})"),
            r"a listener takes no \(in …\): it hears only in the view it is written in",
        )

    def test_in_a_scene(self):
        error(
            f"(real k 0) (scene s (circle c) (on-click c {GO}))",
            "on-click is written inside the body of the view it acts in",
        )

    def test_a_canvas_that_never_shows_the_shape(self):
        error(
            f"(real k 0) (scene s (circle c) (group g (rect r))) (canvas a g (on-click c {GO}))",
            "the canvas a never shows c",
        )

    @pytest.mark.parametrize("kind,src", ON_SHAPES[:-1])
    def test_a_shape_in_a_display(self, kind, src):
        error(
            f"(point p) {SCENE} {FORMULA} (display d f {src})",
            "a display shows no shapes, so c is never in d",
        )

    def test_a_term_in_a_canvas(self):
        error(
            f"{SCENE} {FORMULA} (canvas a s (on-click f.t {GO}))",
            "a canvas shows no terms, so f.t is never in a",
        )

    def test_a_term_of_another_formula(self):
        error(
            rf"(real k 0) {FORMULA} (formula g tex'\term{{u}}{{y}}') (display e g"
            rf" (on-click f.t {GO}))",
            "the display e shows g, not f, so f.t is never in it",
        )

    @pytest.mark.parametrize("kind,src", ON_SHAPES[:-1])
    def test_a_shape_in_a_readout(self, kind, src):
        error(
            f"(point p) {SCENE} (readout ro 'x' {src})",
            f"a readout takes on-live and on-quiet, not {kind}",
        )

    @pytest.mark.parametrize("view", ["(display d f", "(readout d 'x'"])
    def test_on_view_outside_a_canvas(self, view):
        error(
            f"(real k 0) {FORMULA} {view} (on-view {GO}))",
            "on-view plays when a canvas first comes into view, so it is written inside a canvas",
        )

    @pytest.mark.parametrize("view", ["(display d f", "(readout d 'x'"])
    def test_on_pointermove_outside_a_canvas(self, view):
        error(
            f"(point p) {FORMULA} {view} (on-pointermove p))",
            "on-pointermove follows the pointer in a canvas, so it is written inside a canvas",
        )

    def test_a_term_listener_that_terms_do_not_take(self):
        error(
            f"(real k 0) {FORMULA} (display d f (on-dragstart f.t {GO}))",
            "a term takes on-click, on-enter and on-leave",
        )

    def test_something_else_in_a_view_s_let(self):
        error(
            f"{SCENE} (canvas a s (let ((t 2)) (on-click c {GO}) (button bt {GO})))",
            "a view's foreach or let holds listeners only",
        )


class TestOwnViewNamed:
    """Whether a listener on its own view names it inside the view's body is open (mtp-6k7f);
    compiler.OWN_VIEW_NAMED switches to the form that names it."""

    @pytest.fixture(autouse=True)
    def named(self, monkeypatch):
        monkeypatch.setattr("mathterpiece.compiler.OWN_VIEW_NAMED", True)

    @pytest.mark.parametrize("kind", ["on-view", "on-live"])
    def test_it_names_its_view(self, kind):
        m = model(two_canvases(b=f"({kind} b {GO})"))
        assert one(m, kind).data["view"] == m.id("b")

    def test_another_view(self):
        error(two_canvases(b=f"(on-view a {GO})"), "on-view inside b listens to b")

    def test_on_pointermove_on_its_canvas(self):
        m = model(f"(point p) {two_canvases(b='(on-pointermove b p) (on-pointermove c p)')}")
        moves = [o for o in m.objects if o.kind == "on-pointermove"]
        assert [(o.data["shape"], o.data["view"]) for o in moves] == [
            (None, m.id("b")),
            (m.id("c"), None),
        ]


CONTROLS = [
    ("slider", "(slider sl (move k (from 0) (to 1)) (in a))"),
    ("button", f"(button bt (in a) {GO})"),
    ("play", f"(play pl (in a) {GO})"),
    ("toggle", "(bool on) (toggle tg on (in a))"),
]


class TestControls:
    @pytest.mark.parametrize("kind,src", CONTROLS)
    def test_each_control_takes_its_views(self, kind, src):
        m = model(f"{two_canvases()} {src}")
        assert one(m, kind).data["in"] == [m.id("a")]

    def test_any_view(self):
        m = model(
            f"{two_canvases()} {FORMULA} (display d f) (readout ro 'x') (button bt (in a ro d))"
        )
        assert one(m, "button").data["in"] == [m.id("a"), m.id("ro"), m.id("d")]

    def test_more_than_one_view(self):
        m = model(f"{two_canvases()} (button bt (in a b))")
        assert one(m, "button").data["in"] == [m.id("a"), m.id("b")]

    def test_without_it_no_view(self):
        assert one(model(f"{two_canvases()} (button bt)"), "button").data["in"] is None

    @pytest.mark.parametrize("kind,src", CONTROLS)
    def test_it_is_written(self, kind, src):
        d = doc(f"{two_canvases()} {src}")
        o = next(o for o in d["objects"] if o["kind"] == kind)
        assert o["in"] == [d["names"]["a"]]
        assert errors(d) == []

    def test_without_it_nothing_is_written(self):
        d = doc(f"{two_canvases()} (button bt)")
        assert "in" not in next(o for o in d["objects"] if o["kind"] == "button")

    def test_not_a_view(self):
        error(f"{two_canvases()} (button bt) (button bu (in bt))", "bt is a button, not a view")

    def test_a_variable_is_not_a_view(self):
        error(f"{two_canvases()} (button bt (in k))", "k is a variable, not a view")

    def test_an_unknown_name(self):
        error(f"{two_canvases()} (button bt (in nowhere))", "unknown view 'nowhere'")

    def test_a_view_declared_later(self):
        error(
            f"(real k 0) (scene s (circle c)) (button bt (in a) {GO}) (canvas a s)",
            "unknown view 'a': a control names views declared before it",
        )

    def test_not_a_name(self):
        error(f"{two_canvases()} (button bt (in 1))", r"\(in …\) names views, such as \(in a b\)")

    def test_at_least_one(self):
        error(f"{two_canvases()} (button bt (in))", r"\(in …\) names at least one view")

    def test_twice_in_one(self):
        error(f"{two_canvases()} (button bt (in a a))", "a is named twice")

    def test_given_twice(self):
        error(f"{two_canvases()} (button bt (in a) (in b))", "'in' is given twice")

    @pytest.mark.parametrize(
        "view", ["(canvas v (in a) s)", "(readout v 'x' (in a))", "(display v f (in a))"]
    )
    def test_a_view_takes_none(self, view):
        error(f"{two_canvases()} {FORMULA} {view}", r"a view takes no \(in …\)")
