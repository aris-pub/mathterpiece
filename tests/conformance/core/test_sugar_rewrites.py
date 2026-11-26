"""Conformance tests of the rule sugar-rewrites (docs/spec/core.md)."""

from ._shared import (
    CHOREO_ARGUMENT,
    COND_ELSE,
    FREE,
    LOCAL_PART,
    PALETTE_TYPE,
    PARAMETRIC,
    POS_RANDOM,
    RAND,
    SCENE,
    WAIT,
    accepted,
    compile_error,
    itertools,
    pytest,
    rule,
    same_meaning,
    typ,
    value,
)


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
            "(list[real] xs {3 4}) (real v (let ((r 1)) xs.r))",
            "(list[real] xs {3 4}) (real v (let ((r 1)) (. xs r)))",
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

    def test_maybe_is_not_a_type(self):
        compile_error("((maybe real) k none)")

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

    @PARAMETRIC
    def test_parametric(self):
        same_meaning(
            "(scene s (parametric p (range -2 2 (num 5)) (fn t [t (* t t)])))",
            "(scene s (polyline p (points (map (range -2 2 (num 5)) (fn t [t (* t t)])))))",
        )

    @PALETTE_TYPE
    def test_palette(self):
        same_meaning("(palette p (a #'red'))", "(namespace p (color a #'red'))")

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
            RAND + "(rand-seed sd 1) (list[point] corners {[0 0] [1 1]} (const))"
            " (scene s (circle c (pos (or? (pick corners) [0 0])) (r 1)))"
        )

    def test_pos_of_a_free_starting_value(self):
        same_meaning(
            "(scene s (circle c (pos free@[1 2]) (r 1)))",
            "(scene s (circle c (x free@1) (y free@2) (r 1)))",
        )

    def test_foreach_of_several_names(self):
        same_meaning(
            "(scene s (foreach ((i 2) (j 3)) (circle @'c-{i}-{j}' (r 1))))",
            "(scene s (foreach i 2 (foreach j 3 (circle @'c-{i}-{j}' (r 1)))))",
        )
        same_meaning(
            "(scene s (foreach ((i 2)) (circle @'c-{i}' (r 1))))",
            "(scene s (foreach i 2 (circle @'c-{i}' (r 1))))",
        )

    def test_foreach_of_several_names_that_are_the_same(self):
        compile_error("(scene s (foreach ((i 2) (i 3)) (circle @'c-{i}' (r 1))))")

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

    def test_a_control_plays_a_move_as_an_animation_of_that_move(self):
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
