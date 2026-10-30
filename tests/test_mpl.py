import math
import random
from fractions import Fraction
from pathlib import Path

import pytest
from helpers import with_scene
from matplotlib.backend_bases import ResizeEvent
from matplotlib.colors import to_rgba

from mathterpiece.backends.mpl import EvalError, Evaluator, render
from mathterpiece.compiler import compile_model
from mathterpiece.model import Bound, Circle, Model
from mathterpiece.nodes import Name
from mathterpiece.parse import parse

EXAMPLES = Path(__file__).parent.parent / "examples"


def scene(src):
    return compile_model(with_scene(src))


def value(src, name, attr, seed=0):
    scn = scene(src)
    return Evaluator(scn, random.Random(seed)).value(scn[name], attr)


class TestFree:
    def test_free_value(self):
        assert value("(circle 'c' (r 2))", "c", "r") == 2.0

    def test_default(self):
        assert value("(circle 'c')", "c", "fill") == "#000000ff"

    def test_builtin(self):
        assert value("(circle 'c' (r pi))", "c", "r") == math.pi


class TestBound:
    def test_reads_another_attribute(self):
        assert value("(circle 'd' (r 3)) (circle 'c' (r d.r))", "c", "r") == 3.0

    def test_reads_a_param(self):
        assert value("(real 'k' 4) (circle 'c' (r k))", "c", "r") == 4.0

    def test_chain_of_bound_values(self):
        src = "(real 'k' 2) (real 'm' (* k 3)) (circle 'c' (r (+ m 1)))"
        assert value(src, "c", "r") == 7.0

    def test_string_attribute(self):
        src = "(circle 't' (stroke 'teal')) (circle 'c' (fill t.stroke))"
        assert value(src, "c", "fill") == "#008080ff"

    def test_hyphenated_attribute(self):
        src = "(circle 't' (stroke-width 3)) (circle 'c' (r t.stroke-width))"
        assert value(src, "c", "r") == 3.0

    @pytest.mark.parametrize(
        "expr, result",
        [
            ("(+ k 1)", 3.0),
            ("(- k 1)", 1.0),
            ("(- k)", -2.0),
            ("(* k 3)", 6.0),
            ("(/ k 4)", 0.5),
            ("(+ k 1/2)", 2.5),
            ("(+ k 1 2 3)", 8.0),
            ("(- 10 k k)", 6.0),
            ("(/ 8 k 2)", 2.0),
        ],
    )
    def test_arithmetic(self, expr, result):
        assert value(f"(real 'k' 2) (circle 'c' (r {expr}))", "c", "r") == result

    def test_real_attribute_is_a_float(self):
        r = value("(real 'k' 2) (circle 'c' (r (* k 1)))", "c", "r")
        assert type(r) is float

    def test_division_by_zero(self):
        with pytest.raises(EvalError):
            value("(real 'k' 0) (circle 'c' (r (/ 1 k)))", "c", "r")

    def test_value_is_computed_once(self):
        scn = scene("(real 'k' (rand)) (circle 'c' (r k))")
        ev = Evaluator(scn, random.Random(1))
        assert ev.value(scn["c"], "r") == ev.value(scn["k"], "value")


class TestSelf:
    def test_reads_own_attribute(self):
        assert value("(circle 'c' (x 5) (y (* 2 self.x)))", "c", "y") == 10.0

    def test_self_is_the_owner(self):
        src = "(group 'g' (circle 'a' (x 1) (y self.x)) (circle 'b' (x 2) (y self.x)))"
        scn = scene(src)
        ev = Evaluator(scn, random.Random(0))
        assert (ev.value(scn["a"], "y"), ev.value(scn["b"], "y")) == (1.0, 2.0)

    def test_self_of_an_anonymous_object(self):
        scn = scene("(group 'g' (circle _ (x 3) (y self.x)))")
        anon = scn["g"].members[0]
        assert Evaluator(scn, random.Random(0)).value(anon, "y") == 3.0

    def test_cycle_in_a_scene_built_without_the_compiler(self):
        scn = Model()
        scn.add(Circle(name="c", x=Bound(Name(("self", "y"))), y=Bound(Name(("self", "x")))))
        with pytest.raises(EvalError, match="cycle"):
            Evaluator(scn, random.Random(0)).value(scn["c"], "x")


class TestRand:
    def test_range(self):
        scn = scene("(group 'g' (repeat i 200 (circle _ (r (rand 2 3)))))")
        ev = Evaluator(scn, random.Random(0))
        rs = [ev.value(m, "r") for m in scn["g"].members]
        assert all(2 <= r <= 3 for r in rs)
        assert len(set(rs)) > 1

    def test_default_range(self):
        scn = scene("(group 'g' (repeat i 200 (circle _ (r (rand)))))")
        ev = Evaluator(scn, random.Random(0))
        assert all(0 <= ev.value(m, "r") < 1 for m in scn["g"].members)

    def test_same_value_when_read_through_self(self):
        scn = scene("(circle 'c' (r (rand)) (x self.r))")
        ev = Evaluator(scn, random.Random(0))
        assert ev.value(scn["c"], "x") == ev.value(scn["c"], "r")

    def test_seed_makes_it_repeatable(self):
        src = "(circle 'c' (r (rand)))"
        assert value(src, "c", "r", seed=7) == value(src, "c", "r", seed=7)

    def test_two_rands_in_one_expression_differ(self):
        scn = scene("(real 'a' (- (rand) (rand)))")
        assert Evaluator(scn, random.Random(0)).value(scn["a"], "value") != 0.0


class TestGroupsAndIndexing:
    def test_splice_into_arithmetic(self):
        src = "(group 'g' (circle 'a' (r 1)) (circle 'b' (r 2))) (real 's' (+ g.r))"
        assert value(src, "s", "value") == 3.0

    def test_index(self):
        src = "(group 'g' (circle _ (r 4)) (circle _ (r 5))) (real 'k' g[1].r)"
        assert value(src, "k", "value") == 5.0

    def test_negative_index(self):
        src = "(group 'g' (circle _ (r 4)) (circle _ (r 5))) (real 'k' g[-2].r)"
        assert value(src, "k", "value") == 4.0

    def test_splice_reads_bound_members(self):
        src = "(real 'k' 3) (group 'g' (circle 'a' (r k)) (circle 'b' (r 1))) (real 's' (* g.r))"
        assert value(src, "s", "value") == 3.0


class TestText:
    def test_interpolation(self):
        src = "(circle 'disk' (r 2)) (text 't' $'r = {disk.r}')"
        assert value(src, "t", "value") == "r = 2.0"

    def test_splice_joined_with_spaces(self):
        src = "(group 'g' (circle 'a' (r 3.5)) (circle 'b' (r 1.2))) (text 't' $'radii: {g.r}')"
        assert value(src, "t", "value") == "radii: 3.5 1.2"

    def test_param_value(self):
        assert value("(real 'k' 1/2) (text 't' $'{k}')", "t", "value") == "0.5"

    def test_self(self):
        assert value("(text 't' $'at {self.x}' (x 1))", "t", "value") == "at 1.0"


class TestUnevaluatedExpression:
    def test_ratio_arithmetic_stays_exact_until_stored(self):
        scn = Model()
        c = Circle(name="c", r=Bound(parse("(f (/ 1 3))")[0].items[1]))
        scn.add(c)
        assert Evaluator(scn, random.Random(0)).value(c, "r") == float(Fraction(1, 3))

    def test_unknown_name_at_evaluation(self):
        scn = Model()
        c = Circle(name="c", r=Bound(Name(("nope",))))
        scn.add(c)
        with pytest.raises(EvalError, match="nope"):
            Evaluator(scn, random.Random(0)).value(c, "r")


class TestRender:
    @pytest.mark.parametrize("example", sorted(EXAMPLES.glob("*.mtp")), ids=lambda p: p.name)
    def test_examples_render(self, example):
        figures = render(compile_model(parse(example.read_text())), random.Random(0))
        assert len(figures) == 1

    def test_view_box_sets_the_axes_limits_with_y_up(self):
        ((_, ax),) = render(
            scene("(canvas 'cnv' (view-x 1) (view-y -2) (view-width 4) (view-height 3))")
        )
        assert ax.get_xlim() == (1.0, 5.0)
        assert ax.get_ylim() == (-2.0, 1.0)

    def test_x_and_y_have_the_same_scale_like_an_svg_view_box(self):
        ((_, ax),) = render(scene("(canvas 'cnv' (view-width 40) (view-height 10))"))
        assert ax.get_aspect() == 1.0
        assert ax.get_xlim() == (-10.0, 30.0)

    def test_no_ticks_or_labels(self):
        ((_, ax),) = render(scene("(canvas 'cnv')"))
        assert list(ax.get_xticks()) == list(ax.get_yticks()) == []
        assert ax.get_xlabel() == ax.get_ylabel() == ""

    def test_text_is_clipped_at_the_view_like_circles(self):
        ((_, ax),) = render(scene("(text 't' 'hi') (circle 'c') (canvas 'cnv' t c)"))
        text, circle = ax.patches
        assert text.get_clip_on() and circle.get_clip_on()
        assert text.get_clip_box() is not None

    def test_stroke_width_is_in_scene_units(self):
        def widths(transform="", size=None):
            src = (
                "(circle 'a' (stroke 'red') (stroke-width 1))"
                " (text 't' 'hi' (stroke 'red') (stroke-width 2))"
                f" (canvas 'cnv' {transform} a t)"
            )
            ((fig, ax),) = render(scene(src))
            if size is not None:
                fig.set_size_inches(*size)
                fig.canvas.callbacks.process(
                    "resize_event", ResizeEvent("resize_event", fig.canvas)
                )
            (x0, _), (x1, _) = ax.transData.transform([(0, 0), (1, 0)])
            unit = (x1 - x0) * 72 / fig.dpi
            return [p.get_linewidth() / unit for p in ax.patches]

        assert widths() == pytest.approx([1, 2])
        assert widths("(transform (scale 2))") == pytest.approx([2, 4])
        assert widths(size=(3, 9)) == pytest.approx([1, 2])

    def test_no_frame(self):
        ((_, ax),) = render(scene("(canvas 'cnv')"))
        assert not ax.get_frame_on()

    def test_one_figure_per_canvas(self):
        assert len(render(scene("(canvas 'a') (canvas 'b')"))) == 2


VIEW = "(view-x 0) (view-y 0) (view-width 10) (view-height 10)"


def drawn(transform, member="(circle 'c' (x 6) (y 5))", name="c"):
    src = f"(real 'k' 90) {member} (canvas 'cnv' {VIEW} {transform} {name})"
    ((_, ax),) = render(scene(src))
    return ax


def data_position(artist, ax, point):
    return tuple((artist.get_transform() - ax.transData).transform(point))


class TestTransform:
    def test_value_of_a_bound_transform(self):
        m = value("(real 'k' 90) (canvas 'cnv' (transform (rotate k)))", "cnv", "transform")
        assert m.apply(1, 0) == pytest.approx((0, 1))

    def test_another_transform_as_an_argument(self):
        src = (
            "(real 'k' 90) (canvas 'a' (transform (rotate k)))"
            " (canvas 'cnv' (transform a.transform (translate 1 0)))"
        )
        assert value(src, "cnv", "transform").apply(1, 0) == pytest.approx((1, 1))

    def test_bad_argument_at_run_time(self):
        with pytest.raises(EvalError):
            value("(real 'k' 0) (canvas 'cnv' (transform (scale (/ 1 k))))", "cnv", "transform")

    def test_rotate_turns_around_the_view_center(self):
        ax = drawn("(transform (rotate k))")
        (circle,) = ax.patches
        assert data_position(circle, ax, (0, 0)) == pytest.approx((5, 6))

    def test_scale_grows_around_the_view_center(self):
        ax = drawn("(transform (scale 2))")
        (circle,) = ax.patches
        assert data_position(circle, ax, (0, 0)) == pytest.approx((7, 5))
        assert data_position(circle, ax, (1, 0)) == pytest.approx((9, 5))

    def test_translate_moves_the_picture(self):
        ax = drawn("(transform (translate 1 -1))")
        (circle,) = ax.patches
        assert data_position(circle, ax, (0, 0)) == pytest.approx((7, 4))

    def test_text_positions_are_transformed(self):
        ax = drawn("(transform (rotate k))", "(text 't' 'hi' (x 6) (y 5))", "t")
        (text,) = ax.patches
        assert data_position(text, ax, (0, 0)) == pytest.approx((5, 6))

    def test_letters_turn_with_the_transform(self):
        def size(transform):
            ((_, ax),) = render(scene(f"(text 't' 'hhhhhhhh') (canvas 'cnv' {transform} t)"))
            (text,) = ax.patches
            box = text.get_path().transformed(text.get_transform() - ax.transData).get_extents()
            return box.width, box.height

        width, height = size("")
        turned_width, turned_height = size("(transform (rotate 90))")
        assert width > height
        assert turned_height == pytest.approx(width) and turned_width == pytest.approx(height)

    def test_letters_scale_with_the_transform(self):
        def height(transform, font_size=1):
            src = f"(text 't' 'H' (font-size {font_size})) (canvas 'cnv' {transform} t)"
            ((_, ax),) = render(scene(src))
            (text,) = ax.patches
            return (
                text.get_path()
                .transformed(text.get_transform() - ax.transData)
                .get_extents()
                .height
            )

        assert height("(transform (scale 2))") == pytest.approx(2 * height(""))
        assert height("", font_size=3) == pytest.approx(3 * height(""))

    def test_text_is_drawn_with_its_fill(self):
        ((_, ax),) = render(scene("(text 't' 'hi' (fill 'red')) (canvas 'cnv' t)"))
        (text,) = ax.patches
        assert text.get_facecolor() == to_rgba("red")
        assert text.get_label() == "hi"

    def test_view_box_is_unchanged_by_the_transform(self):
        ax = drawn("(transform (rotate k) (scale 2))")
        assert (ax.get_xlim(), ax.get_ylim()) == ((0, 10), (0, 10))


def k_value(expr, k=2):
    return value(f"(real 'k' {k}) (circle 'disk' (x 3) (y 4)) (real 'v' {expr})", "v", "value")


def k_text(expr, k=2):
    return value(f"(real 'k' {k}) (text 't' {expr})", "t", "value")


class TestConditionals:
    @pytest.mark.parametrize(
        "cond, result",
        [
            ("(< k 3)", "a"),
            ("(< k 2)", "b"),
            ("(<= k 2)", "a"),
            ("(> k 1/2)", "a"),
            ("(>= k 3)", "b"),
            ("(= k 2)", "a"),
            ("(!= k 2)", "b"),
        ],
    )
    def test_comparisons_in_if(self, cond, result):
        assert k_text(f"(if {cond} 'a' 'b')") == result

    def test_cond_first_true(self):
        assert k_text("(cond ((< k 1) 'a') ((< k 3) 'b') (else 'c'))") == "b"

    def test_cond_else(self):
        assert k_text("(cond ((< k 1) 'a') (else 'c'))") == "c"

    def test_if_only_evaluates_the_chosen_branch(self):
        assert k_value("(if (< k 3) 1 (/ 1 (- k 2)))") == 1.0

    def test_cond_stops_at_the_first_true_clause(self):
        assert k_value("(cond ((< k 3) 1) ((< (/ 1 (- k 2)) 0) 2) (else 3))") == 1.0

    def test_numeric_branches_widen(self):
        assert k_value("(if (< k 3) 1 2.5)") == 1.0


class TestPowerAndSqrt:
    @pytest.mark.parametrize(
        "expr, result", [("(^ k 3)", 8.0), ("(^ k -1)", 0.5), ("(^ k 0.5)", 2**0.5)]
    )
    def test_power(self, expr, result):
        assert k_value(expr) == result

    def test_power_of_negative_base_to_fraction(self):
        with pytest.raises(EvalError):
            k_value("(^ k 0.5)", k=-2)

    def test_zero_to_negative_power(self):
        with pytest.raises(EvalError):
            k_value("(^ k -1)", k=0)

    def test_mod(self):
        assert k_value("(mod k 3)", k=7) == 1.0
        assert k_value("(mod k 3)", k=-1) == 2.0

    def test_mod_by_zero(self):
        with pytest.raises(EvalError):
            k_value("(mod 1 k)", k=0)

    def test_sqrt(self):
        assert k_value("(sqrt k)", k=9) == 3.0

    @pytest.mark.parametrize(
        "expr, k, result",
        [("(sind k)", 30, 0.5), ("(cosd k)", 90, 0.0), ("(to-rad k)", 180, math.pi)],
    )
    def test_angles(self, expr, k, result):
        assert k_value(expr, k=k) == pytest.approx(result)

    def test_tand_at_a_right_angle(self):
        with pytest.raises(EvalError):
            k_value("(tand k)", k=90)

    def test_sqrt_of_negative(self):
        with pytest.raises(EvalError):
            k_value("(sqrt k)", k=-1)


class TestDist:
    def test_two_objects(self):
        assert (
            value("(circle 'a') (circle 'b' (x 3) (y 4)) (real 'd' (dist a b))", "d", "value")
            == 5.0
        )

    def test_with_self(self):
        src = "(circle 'a' (x 1) (y 1)) (circle 'b' (x 4) (y 5) (r (dist self a)))"
        assert value(src, "b", "r") == 5.0

    def test_four_numbers(self):
        assert k_value("(dist 0 0 disk.x disk.y)") == 5.0

    def test_bound_coordinates(self):
        src = "(real 'k' 3) (circle 'a' (x k)) (circle 'b' (y 4)) (real 'd' (dist a b))"
        assert value(src, "d", "value") == 5.0


class TestFormatSpecs:
    def test_real(self):
        assert k_text("$'{k:.1f}'", k=2) == "2.0"
        assert k_text("$'{k:.3e}'", k=1234.5) == "1.234e+03"

    def test_int_while_drawing(self):
        src = (
            "(motif 'm' (params (n 7)) (circle 'c')) (m 'd')"
            " (slider 's' (animation (d.n (transition (from 0) (to 99)))))"
            " (text 't' $'{d.n:03d}')"
        )
        m = scene(src)
        ev = Evaluator(m, random.Random(0))
        assert ev.value(m["t"], "value") == "007"
        ev.write(m["d"], "n", 42)
        assert ev.value(m["t"], "value") == "042"


class TestDotsExample:
    def test_each_dot_is_colored_by_the_circle_it_touches(self):
        scn = compile_model(parse((EXAMPLES / "dots.mtp").read_text()))
        ev = Evaluator(scn, random.Random(0))
        teal, red = scn["teal_c"], scn["red_c"]
        colors = set()

        def touches(dot, c):
            return math.dist(ev.point(dot), ev.point(c)) < ev.value(dot, "r") + ev.value(c, "r")

        for dot in scn["dots"].members:  # ty: ignore[unresolved-attribute]
            # The strokes are checked colors (#rrggbbaa); 'gray' is chosen while drawing, so it
            # stays as written.
            expected = (
                "#008080ff" if touches(dot, teal) else "#ff0000ff" if touches(dot, red) else "gray"
            )
            assert ev.value(dot, "fill") == expected
            colors.add(expected)
        assert colors == {"#008080ff", "#ff0000ff", "gray"}


class TestRef:
    def test_reads_through_ref(self):
        assert value("(circle 'a' (r 2)) (circle 'b' (r (ref 'a.r')))", "b", "r") == 2.0


class TestInfinity:
    def test_reads_infinity(self):
        m = scene("(real 'k' infty) (real 'j' (- infty))")
        ev = Evaluator(m, random.Random(0))
        assert ev.value(m["k"], "value") == math.inf
        assert ev.value(m["j"], "value") == -math.inf
