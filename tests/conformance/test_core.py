"""Conformance tests for docs/spec/core.md."""

import itertools

import pytest

from .support import (
    REJECTION,
    accepted,
    compile_error,
    in_folder,
    mtpc,
    rejected,
    same_meaning,
    value,
)


def typ(src, name):
    attribute = accepted(src).get(name).value
    return attribute.expr.type if attribute.bound else attribute.type


rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


LOCAL_PART = xfail("mtp-ydd4.7.5", "each part after the first of a name is read as an attribute")
LIKE_INSTANCE = xfail("mtp-ydd4.7.20", "like on an instance copies neither pointer-events nor clip")
WAIT = xfail("mtp-ydd4.7.21", "wait makes no transition object, while its rewrite does")
PALETTE_TYPE = xfail("mtp-ydd4.7.22", "a palette has the type palette, not namespace")
COND_ELSE = xfail("mtp-ydd4.7.46", "(cond (else V)) is marked const, while V is not")
IMPORT_DOT = xfail("mtp-ydd4.7.47", "after (import F), (. F N) is an unknown name")
POS_RANDOM = xfail(
    "mtp-ydd4.7.25", "pos compiles its point once, so a random call in it is one site"
)
CHOREO_ARGUMENT = xfail("mtp-08wd.5", "an argument of a choreo must be known when compiling")
MEMBER_BY_NAME = xfail("mtp-ydd4.7.19", "a member of a namespace is read as a key, not by its name")
ANIMATION_STEP = xfail("mtp-ydd4.7.26", "an animation's body does not accept the head animation")
BOUNDED_LIST = xfail("mtp-ydd4.7.37", "a foreach over a list whose length is not known is an error")
STEP_EASE = xfail("mtp-ydd4.7.40", "step and step-ease are read only as the value of an ease")

SCENE = "(scene s (circle p (r 1)) (group g (circle q (r 2))))\n"
RAND = "(import rand rand rand-int pick shuffle next-seed roll-dice) "


@rule("kinds-of-form")
class TestKindsOfForm:
    def test_a_library_head_may_be_declared_again(self):
        assert value("(func max ((real a) (real b)) b) (real v (max 1 2))", "v") == 2

    @pytest.mark.parametrize("head", ["if", "when", "foreach", "circle"])
    def test_a_core_or_sugar_head_may_not(self, head):
        compile_error(f"(func {head} ((real a)) a)")


@rule("sugar-form")
class TestSugarForm:
    def test_a_rewrite_may_resolve_a_name(self):
        # p.r is rewritten into (. p r) by reading which shape p names.
        same_meaning(SCENE + "(real v p.r)", SCENE + "(real v (. p r))")

    def test_a_sugar_form_means_exactly_its_rewrite(self):
        same_meaning(
            "(bool c true) (real|none v (when c 1))", "(bool c true) (real|none v (if c 1 none))"
        )


@rule("library-form")
class TestLibraryForm:
    def test_a_call_of_a_built_in_is_a_call(self):
        assert value("(real v (max 1 2))", "v") == 2

    def test_the_standard_library_is_ordinary_declarations(self, tmp_path):
        m = in_folder(tmp_path, {}, "(import math)\n(real v (math.clamp 5 0 2))\n")
        assert m.get("v").value.value == 2
        # A declaration of the source may take a name that the library declares.
        accepted("(func clamp ((real x)) x) (real v (clamp 5))")

    def test_a_declared_function_takes_the_name_of_an_operator(self):
        assert value("(func + ((real a) (real b)) 7) (real v (+ 1 2))", "v") == 7


FREE = "(bool a true) (bool b true) (bool c false)\n"


@rule("sugar-rewrites")
class TestSugarRewrites:
    def test_a_name_with_parts(self):
        same_meaning(SCENE + "(real v p.r)", SCENE + "(real v (. p r))")

    def test_a_chain_of_parts_is_read_from_left_to_right(self):
        same_meaning(
            "(point q [1 2]) (scene s (circle p (pos q) (r 1))) (real v p.pos.x)",
            "(point q [1 2]) (scene s (circle p (pos q) (r 1))) (real v (. (. p pos) x))",
        )
        same_meaning(SCENE + "(real v g[0].r)", SCENE + "(real v (. (. g 0) r))")

    @LOCAL_PART
    def test_a_part_is_rewritten_with_the_name_in_scope(self):
        same_meaning(
            "(list[real] xs [3 4]) (real v (let ((r 1)) xs.r))",
            "(list[real] xs [3 4]) (real v (let ((r 1)) (. xs r)))",
        )

    def test_when(self):
        same_meaning(FREE + "(real|none v (when a 1))", FREE + "(real|none v (if a 1 none))")

    def test_when_takes_exactly_two_arguments(self):
        compile_error(FREE + "(real|none v (when a 1 2))")

    def test_cond(self):
        same_meaning(
            FREE + "(real v (cond (a 1) (b 2) (else 3)))",
            FREE + "(real v (if a 1 (if b 2 3)))",
        )

    @COND_ELSE
    def test_cond_with_only_else(self):
        # The compiler makes v const, while (real v 3) is a free variable that a writer may write.
        same_meaning("(real v (cond (else 3)))", "(real v 3)")

    @pytest.mark.parametrize("a, b, c", list(itertools.product([True, False], repeat=3)))
    def test_and(self, a, b, c):
        known = f"(bool a {str(a).lower()} (const)) (bool b {str(b).lower()} (const))"
        known += f" (bool c {str(c).lower()} (const))"
        assert value(known + " (bool v (and a b c))", "v") == value(
            known + " (bool v (if a (if b c false) false))", "v"
        )
        assert value(known + " (bool v (and a))", "v") == a

    @pytest.mark.parametrize("a, b, c", list(itertools.product([True, False], repeat=3)))
    def test_or(self, a, b, c):
        known = f"(bool a {str(a).lower()} (const)) (bool b {str(b).lower()} (const))"
        known += f" (bool c {str(c).lower()} (const))"
        assert value(known + " (bool v (or a b c))", "v") == value(
            known + " (bool v (if a true (if b true c)))", "v"
        )
        assert value(known + " (bool v (or a))", "v") == a

    def test_and_and_or_have_the_type_of_their_rewrite(self):
        assert typ(FREE + "(bool v (and a b c))", "v") == typ(
            FREE + "(bool v (if a (if b c false) false))", "v"
        )
        assert typ(FREE + "(bool v (or a b c))", "v") == typ(
            FREE + "(bool v (if a true (if b true c)))", "v"
        )

    def test_maybe(self):
        same_meaning("((maybe real) k none)", "(real|none k none)")

    def test_the_type_colormap(self):
        same_meaning(
            "(func f ((colormap m)) (m 0.5)) (colormap cm ['red' 'blue']) (color v (f cm))",
            "(func f ((func[real color] m)) (m 0.5)) (colormap cm ['red' 'blue']) (color v (f cm))",
        )

    def test_a_declared_type(self):
        compile_error("(type pos real (>= 0)) (pos k -1)")
        a = accepted("(type pos real (>= 0)) (pos k 1)").get("k").value.type
        b = accepted("((real (>= 0)) k 1)").get("k").value.type
        assert (a.base, a.constraints) == (b.base, b.constraints)

    def test_range_of_one_argument(self):
        same_meaning(
            "(int n 3 (>= 0) (<= 5)) (list[int] v (range n))",
            "(int n 3 (>= 0) (<= 5)) (list[int] v (range 0 n (gap 1)))",
        )

    def test_a_random_function_follows_the_default_seed(self):
        same_meaning(
            RAND + "(rand-seed s 1) (real v (rand 0 1))",
            RAND + "(rand-seed s 1) (real v (rand 0 1 (seed s)))",
        )

    def test_by_any_name_that_an_import_gives(self, tmp_path):
        a = in_folder(tmp_path, {}, "(import rand) (real v (rand.rand 0 1))")
        assert (a.id("rand.seed"), None) in a.get("v").value.deps
        compile_error("(import rand) (rand-seed s 1) (real v (rand.rand 0 1))", tmp_path / "a.mtp")

    def test_a_seed_of_a_declared_type(self):
        m = accepted(RAND + "(type dice rand-seed) (dice s 1) (real v (rand 0 1))")
        assert (m.id("s"), None) in m.get("v").value.deps

    def test_with_no_seed_the_seed_of_rand(self, tmp_path):
        same_meaning(
            "(import rand rand) (real v (rand 0 1))",
            "(import rand rand seed) (real v (rand 0 1 (seed seed)))",
            tmp_path / "a.mtp",
        )

    def test_roll_dice_with_no_seed(self):
        same_meaning(
            RAND + "(rand-seed s 1) (button b (animation (roll-dice)))",
            RAND + "(rand-seed s 1) (button b (animation (roll-dice s)))",
        )

    def test_roll_dice_with_no_seed_by_the_name_of_the_file(self, tmp_path):
        same_meaning(
            "(import rand) (button b (animation (rand.roll-dice)))",
            "(import rand) (button b (animation (rand.roll-dice rand.seed)))",
            tmp_path / "a.mtp",
        )

    def test_roll_dice_is_its_choreo(self):
        same_meaning(
            RAND + "(rand-seed s 1) (button b (animation (roll-dice s)))",
            RAND + "(rand-seed s 1) (button b (animation (set s (next-seed s))))",
        )

    def test_roll_dice_needs_a_seed(self):
        compile_error(RAND + "(real k 1) (button b (animation (roll-dice k)))")

    def test_roll_dice_with_several_seeds(self):
        compile_error(RAND + "(rand-seed s 1) (rand-seed t 2) (button b (animation (roll-dice)))")

    def test_set(self):
        same_meaning(
            "(real k 0) (button b (animation (set k 3)))",
            "(real k 0) (button b (animation (move k (to 3) (duration 0))))",
        )

    def test_set_wherever_a_move_is_written(self):
        same_meaning(
            "(real k 0) (button b (set k 3))", "(real k 0) (button b (move k (to 3) (duration 0)))"
        )
        same_meaning(
            SCENE + "(real k 0) (canvas v s (on-click p (set k 3)))",
            SCENE + "(real k 0) (canvas v s (on-click p (move k (to 3) (duration 0))))",
        )

    def test_set_takes_a_target_and_a_value(self):
        compile_error("(real k 0) (button b (animation (set k)))")
        compile_error("(real k 0) (button b (animation (set k 1 2)))")

    def test_import(self, tmp_path):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n"}
        a = in_folder(tmp_path, lib, "(import lib)\n(real v (lib.twice 2))\n")
        assert a.get("v").value.value == 4

    @IMPORT_DOT
    def test_import_and_the_dot_form(self, tmp_path):
        lib = {"lib.mtp": "(real k 3 (const))\n"}
        m = in_folder(tmp_path, lib, "(import lib)\n(real v (. lib k))\n")
        assert m.get("v").value.value == 3

    def test_import_of_names(self, tmp_path):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n"}
        m = in_folder(tmp_path, lib, "(import lib twice)\n(real v (twice 2))\n")
        assert m.get("v").value.value == 4

    def test_import_of_a_name_that_the_file_does_not_declare(self, tmp_path):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n"}
        with pytest.raises(REJECTION):
            in_folder(tmp_path, lib, "(import lib thrice)\n")

    def test_import_of_a_name_that_the_source_declares(self, tmp_path):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n"}
        with pytest.raises(REJECTION):
            in_folder(tmp_path, lib, "(import lib twice)\n(func twice ((real x)) x)\n")

    def test_a_file_imported_twice_is_put_in_once(self, tmp_path):
        files = {
            "lib.mtp": "(color ink 'navy')\n",
            "other.mtp": "(import lib)\n(color pen lib.ink)\n",
        }
        m = in_folder(tmp_path, files, "(import lib)\n(import other)\n(color v lib.ink)\n")
        assert [o.name for o in m.objects].count("lib.ink") == 1

    @PALETTE_TYPE
    def test_palette(self):
        same_meaning("(palette p (a 'red'))", "(namespace p (color a 'red'))")

    def test_like_on_a_shape(self):
        same_meaning(
            "(scene s (circle a (r 2) (fill 'red')) (circle b (like a) (fill 'blue')))",
            "(scene s (circle a (r 2) (fill 'red')) (circle b (fill 'blue') (r 2)))",
        )

    def test_like_copies_what_the_items_read(self):
        src = "(real k 1 (>= 0)) (scene s (circle a (r (* 2 k))) (circle b (like a)))"
        same_meaning(
            src, "(real k 1 (>= 0)) (scene s (circle a (r (* 2 k))) (circle b (r (* 2 k))))"
        )

    def test_like_splits_pos(self):
        same_meaning(
            "(scene s (circle a (pos [1 2]) (r 1)) (circle b (like a) (x 5)))",
            "(scene s (circle a (pos [1 2]) (r 1)) (circle b (x 5) (y (. [1 2] 1)) (r 1)))",
        )

    def test_like_on_a_text_copies_its_string(self):
        same_meaning(
            "(scene s (text a 'hi' (halign 'start')) (text b (like a) (x 1)))",
            "(scene s (text a 'hi' (halign 'start')) (text b 'hi' (x 1) (halign 'start')))",
        )

    def test_like_of_a_shape_of_another_kind_is_an_error(self):
        compile_error("(scene s (circle a (r 1)) (rect b (like a)))")

    def test_like_of_a_group_is_an_error(self):
        compile_error("(scene s (group a (circle_ (r 1))) (group b (like a)))")

    def test_like_on_a_font(self):
        same_meaning(
            "(font a (size 12) (weight 700)) (font b (like a) (size 14))",
            "(font a (size 12) (weight 700)) (font b (size 14) (weight 700))",
        )

    def test_like_on_a_term(self):
        same_meaning(
            "(formula f tex'\\term{a}{x}\\term{b}{y}' (term a (fill 'red')) (term b (like a)))",
            "(formula f tex'\\term{a}{x}\\term{b}{y}' (term a (fill 'red')) (term b (fill 'red')))",
        )

    def test_like_on_a_move(self):
        same_meaning(
            "(real k 0) (transition t k (to 1) (duration 2)) (button b (animation (move k (like t) "
            "(to 3))))",
            "(real k 0) (transition t k (to 1) (duration 2)) (button b (animation (move k (to 3) "
            "(duration 2))))",
        )

    @LIKE_INSTANCE
    def test_like_on_an_instance_copies_its_pointer_events(self):
        motif = "(motif m () (circle_ (r 1)))\n"
        same_meaning(
            motif + "(scene s (m a (pointer-events false)) (m b (like a)))",
            motif + "(scene s (m a (pointer-events false)) (m b (pointer-events false)))",
        )

    def test_pointer_events_on_a_group(self):
        same_meaning(
            "(scene s (group g (pointer-events false) (circle c (r 1))))",
            "(scene s (group g (defaults (pointer-events false)) (circle c (r 1))))",
        )

    def test_pointer_events_and_a_default_of_it(self):
        compile_error(
            "(scene s (group g (pointer-events false) (defaults (pointer-events true)) (circle c "
            "(r 1))))"
        )

    def test_defaults_on_a_group(self):
        same_meaning(
            "(scene s (group g (defaults (fill 'red')) (circle c (r 1)) (circle d (r 1) (fill "
            "'blue'))))",
            "(scene s (group g (circle c (r 1) (fill 'red')) (circle d (r 1) (fill 'blue'))))",
        )

    def test_defaults_at_any_depth_the_nearest_container_first(self):
        same_meaning(
            "(scene s (group g (defaults (fill 'red')) (group h (defaults (fill 'blue')) (circle c "
            "(r 1)))))",
            "(scene s (group g (group h (circle c (r 1) (fill 'blue')))))",
        )

    def test_a_default_that_no_container_gives(self):
        compile_error("(scene s (group g (defaults (r 2)) (circle c)))")

    def test_defaults_in_a_formula(self):
        same_meaning(
            "(formula f (defaults (fill 'red')) tex'\\term{a}{x}\\term{b}{y}' (term a (fill "
            "'blue')))",
            "(formula f tex'\\term{a}{x}\\term{b}{y}' (term a (fill 'blue')) (term b (fill "
            "'red')))",
        )

    def test_dash_of_one_argument(self):
        same_meaning(
            "(scene s (line l (to [1 1]) (dash [4 2])))",
            "(scene s (line l (to [1 1]) (dash [4 2] 0)))",
        )

    def test_pos_of_a_literal_list(self):
        same_meaning(
            "(scene s (circle c (pos [1 2]) (r 1)))", "(scene s (circle c (x 1) (y 2) (r 1)))"
        )

    def test_pos_of_a_point(self):
        same_meaning(
            "(point q [1 2]) (scene s (circle c (pos q) (r 1)))",
            "(point q [1 2]) (scene s (circle c (x (. q 0)) (y (. q 1)) (r 1)))",
        )

    @POS_RANDOM
    def test_pos_of_a_random_point_is_an_error(self):
        compile_error(
            RAND + "(rand-seed sd 1) (list[point] corners [[0 0] [1 1]] (const))"
            " (scene s (circle c (pos (or? (pick corners) [0 0])) (r 1)))"
        )

    def test_pos_of_a_free_starting_value(self):
        same_meaning(
            "(scene s (circle c (pos free@[1 2]) (r 1)))",
            "(scene s (circle c (x free@1) (y free@2) (r 1)))",
        )

    def test_foreach_of_several_names(self):
        same_meaning(
            "(scene s (foreach ((i 2) (j 3)) (circle #'c-{i}-{j}' (r 1))))",
            "(scene s (foreach i 2 (foreach j 3 (circle #'c-{i}-{j}' (r 1)))))",
        )
        same_meaning(
            "(scene s (foreach ((i 2)) (circle #'c-{i}' (r 1))))",
            "(scene s (foreach i 2 (circle #'c-{i}' (r 1))))",
        )

    def test_foreach_of_several_names_that_are_the_same(self):
        compile_error("(scene s (foreach ((i 2) (i 3)) (circle #'c-{i}' (r 1))))")

    @WAIT
    def test_wait(self):
        same_meaning(
            "(real k 0) (button b (animation (wait 1) (move k (to 1) (duration 1))))",
            "(real k 0) (button b (animation (move none (duration 1)) (move k (to 1) (duration "
            "1))))",
        )

    def test_an_animation_of_several_items(self):
        same_meaning(
            "(real k 0) (animation a (move k (to 1) (duration 1)) (move k (to 2) (duration 1)))",
            "(real k 0) (animation a (in-order (move k (to 1) (duration 1)) (move k (to 2) "
            "(duration 1))))",
        )

    def test_a_move_in_place_of_an_animation(self):
        same_meaning(
            "(real k 0) (button b (move k (to 1) (duration 1)))",
            "(real k 0) (button b (animation (move k (to 1) (duration 1))))",
        )

    def test_a_move_and_an_animation_on_one_control(self):
        compile_error(
            "(real k 0) (button b (move k (to 1) (duration 1)) (animation (move k (to 2) (duration "
            "1))))"
        )

    # What the two spellings of a drag do is checked with the runtime, in
    # web/test/conformance/core.test.ts.
    @pytest.mark.parametrize("target", ["p.pos", "p.x", "p.y"])
    def test_on_drag_of_a_part_of_the_dragged_shape(self, target):
        accepted(SCENE + f"(canvas v s (on-drag p {target}))")

    def test_on_drag_of_another_name_is_an_error(self):
        compile_error("(real k 0)" + SCENE + "(canvas v s (on-drag p k))")

    def test_a_use_of_a_choreo(self):
        same_meaning(
            "(real k 0) (choreo pulse ((real t 1)) (move k (to t) (duration 1))) (button b (pulse "
            "2))",
            "(real k 0) (button b (animation (move k (to 2) (duration 1))))",
        )

    def test_a_use_of_a_choreo_with_a_default(self):
        same_meaning(
            "(real k 0) (choreo pulse ((real t 1)) (move k (to t) (duration 1))) (button b "
            "(pulse))",
            "(real k 0) (button b (animation (move k (to 1) (duration 1))))",
        )

    def test_a_use_of_a_choreo_with_too_few_arguments(self):
        compile_error(
            "(real k 0) (choreo pulse ((real t)) (move k (to t) (duration 1))) (button b (pulse))"
        )

    @CHOREO_ARGUMENT
    def test_an_argument_of_a_choreo_may_be_any_expression_allowed_in_its_place(self):
        accepted(
            "(real k 0) (real j 1) (choreo pulse ((real t 1)) (move k (to t) (duration 1)))"
            " (button b (pulse (* 2 j)))"
        )


@rule("drag-group-translate")
class TestDragGroupTranslate:
    def test_a_drag_of_a_group_is_compiled(self):
        # What the drag writes is shown by the runtime: web/test/conformance/core.test.ts.
        accepted("(scene s (group g (circle c (r 1)))) (canvas v s (on-drag g g.pos))")


@rule("foreach-count")
class TestForeachCount:
    def test_a_count_means_a_range(self):
        same_meaning(
            "(scene s (foreach k 3 (circle #'c-{k}' (r 1))))",
            "(scene s (foreach k (range 3) (circle #'c-{k}' (r 1))))",
        )


@rule("foreach-bounded-length")
class TestForeachBoundedLength:
    def test_a_count_known_only_while_drawing_makes_its_upper_bound_of_copies(self):
        d = mtpc("(int n 3 (>= 0) (<= 5)) (scene s (foreach k n (circle #'c-{k}' (r 1))))")
        assert {f"c-{k}" for k in range(5)} <= set(d["names"])
        assert "c-5" not in d["names"]

    @BOUNDED_LIST
    def test_a_range_known_only_while_drawing(self):
        d = mtpc("(int n 3 (>= 0) (<= 5)) (scene s (foreach k (range n) (circle #'c-{k}' (r 1))))")
        assert {f"c-{k}" for k in range(5)} <= set(d["names"])

    def test_with_no_upper_bound_it_is_an_error(self):
        compile_error("(int n 3 (>= 0)) (scene s (foreach k n (circle #'c-{k}' (r 1))))")


@rule("dot-name-part")
class TestDotPart:
    def test_an_attribute(self):
        m = accepted(SCENE + "(real v (. q r))")
        assert m.get("v").value.expr.args[:2] == (m.id("q"), "r")

    def test_a_position(self):
        assert value("(list[real] xs [3 4] (const)) (real v (. xs 1))", "v") == 4

    def test_a_member_of_a_group_by_its_position(self):
        m = accepted(SCENE + "(real v (. (. g 0) r))")
        assert m.get("v").value.expr.args[:2] == (m.id("q"), "r")

    @LOCAL_PART
    def test_a_name_that_is_no_attribute_is_an_expression(self):
        assert value("(list[real] xs [3 4] (const)) (real v (let ((r 1)) xs.r))", "v") == 4

    @MEMBER_BY_NAME
    def test_a_member_is_read_by_its_name(self):
        assert (
            value(
                "(color yellow 'red') (namespace n (color yellow 'gold')) (color v (. n yellow))",
                "v",
            )
            == "#ffd700ff"
        )


@rule("animation-step")
class TestAnimationStep:
    @ANIMATION_STEP
    def test_an_animation_as_a_step(self):
        accepted(
            "(real k 0) (animation a (move k (to 1) (duration 1))"
            " (animation (loop 2) (move k (to 2) (duration 1))))"
        )


@rule("names-from-values")
class TestNamesFromValues:
    def test_a_name_built_from_the_variable_of_a_foreach(self):
        d = mtpc(
            "(scene s (foreach k 3 (circle #'d-{k}' (pos [k 0])"
            " (r (if (= k 0) 1 (/ #'d-{(- k 1)}'.r 2))))))"
        )
        assert set(d["names"]) >= {"d-0", "d-1", "d-2"}

    def test_a_name_that_names_no_declaration_before_it_is_an_error(self):
        rejected("(scene s (foreach k 2 (circle #'d-{k}' (r #'d-{(+ k 1)}'.r))))")


@rule("library-form")
@STEP_EASE
def test_step_is_a_library_function_that_a_declaration_may_replace():
    compile_error(
        "(real step 3) (real k 0) (button b (animation (move k (to 1) (duration 1) (ease (step "
        "2)))))"
    )
