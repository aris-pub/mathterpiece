"""Conformance tests for docs/spec/binding-time.md."""

import pytest

from .support import accepted, compile_error, free, is_bound, mtpc, obj, same_meaning, value

rule = pytest.mark.rule


def xfail(bead: str | None, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}" if bead else why)


OBJECT_ARGUMENT = xfail(None, "a call with an object as its argument is not folded")
RANDOM_NAMES = xfail(None, "the compiler names choice pick, and shuffled shuffle")
PAGE_READ = xfail(None, "a variable at the top level may read a control")

SLIDER = "(slider sz (animation (move size (from 0) (to 2) (duration 0))))"


@rule("known-when-compiling")
class TestKnownWhenCompiling:
    def test_a_const_container(self):
        assert value("(real c (* 2 3) (const)) (real v (+ c 1))", "v") == 7

    def test_a_bound_container_whose_expression_is_known(self):
        assert value("(real c 3 (const)) (real d (* 2 c)) (real v (+ d 1))", "v") == 7

    def test_a_function_and_a_parameter_whose_argument_is_known(self):
        assert value("(real c 3 (const)) (func f ((real x)) (* 2 x)) (real v (f c))", "v") == 6

    def test_a_built_in_function(self):
        assert value("(real c 3 (const)) (real v (max c 5))", "v") == 5

    def test_a_let_name_whose_value_is_known(self):
        assert value("(real c 3 (const)) (real v (let ((k (* 2 c))) (+ k 1)))", "v") == 7

    def test_a_foreach_name_is_known_in_each_copy(self):
        d = mtpc("(real a 1 (>= 0)) (scene s (foreach i 2 (circle @'c-{i}' (r (if (= i 0) 1 a)))))")
        assert free(d, "c-0", "r") == 1
        assert "bound" in obj(d, "c-1")["attrs"]["r"]

    def test_a_name_that_refers_to_an_object(self):
        assert value("(scene s (circle c (r 1))) (string v c.name)", "v") == "c"

    @OBJECT_ARGUMENT
    def test_a_call_whose_argument_is_an_object(self):
        assert value("(func f ((circle k)) 1) (scene s (circle c (r 1))) (real v (f c))", "v") == 1

    def test_a_free_container_is_known_only_while_drawing(self):
        assert is_bound("(real a 1) (real v (* 2 a))", "v")
        assert is_bound("(real a 1) (func f ((real x)) (* 2 x)) (real v (f a))", "v")
        assert is_bound("(real a 1) (real v (let ((k (* 2 a))) (+ k 1)))", "v")

    def test_a_font_is_known_only_while_drawing(self):
        assert is_bound("(font f (size 12)) (real v f.size)", "v")

    def test_a_random_call_is_known_only_while_drawing(self):
        assert is_bound("(import rand rand) (rand-seed sd 1) (real v (rand 0 1))", "v")
        assert is_bound("(import rand rand-int) (rand-seed sd 1) (int v (rand-int 1 6))", "v")

    @RANDOM_NAMES
    def test_choice_and_shuffled_are_known_only_while_drawing(self):
        src = "(import rand choice shuffled) (rand-seed sd 1) "
        assert is_bound(src + "(int|none v (choice {1 2}))", "v")
        assert is_bound(src + "(list[int] v (shuffled {1 2}))", "v")


@rule("foreach-copies")
class TestForeachCopies:
    def test_one_copy_per_item_of_a_known_list(self):
        d = mtpc("(scene s (foreach k {1 2 3} (circle @'c-{k}' (r k))))")
        assert [free(d, f"c-{k}", "r") for k in (1, 2, 3)] == [1, 2, 3]
        assert len(obj(d, "s")["members"]) == 3

    def test_one_copy_per_item_of_a_list_whose_items_are_known_only_while_drawing(self):
        d = mtpc("(real a 1) (list[real] xs {a 0 1}) (scene s (foreach k xs (circle_ (r 1))))")
        assert len(obj(d, "s")["members"]) == 3


@rule("free-starting-value")
class TestFreeStartingValue:
    def test_a_start_known_when_compiling_is_folded(self):
        d = mtpc("(real c 3 (const)) (real r free@(* 2 c))")
        assert free(d, "r") == 6

    def test_the_container_is_free_and_a_writer_may_write_to_it(self):
        accepted(
            "(real c 3 (const)) (real r free@(* 2 c))"
            " (slider sl (animation (move r (from 0) (to 1) (duration 0))))"
        )
        accepted(
            "(real a 1) (real r free@(* 2 a))"
            " (slider sl (animation (move r (from 0) (to 1) (duration 0))))"
        )

    def test_a_start_known_only_while_drawing_is_not_bound(self):
        assert not is_bound("(real a 1) (real v free@(* 2 a))", "v")
        assert not is_bound("(import rand rand) (rand-seed sd 1) (real v free@(rand 0 1))", "v")

    def test_free_at_is_the_form_free(self):
        same_meaning("(real a 1) (real v free@(* 2 a))", "(real a 1) (real v (free (* 2 a)))")


@rule("what-reads-what")
class TestWhatReadsWhat:
    def test_every_expression_may_read_the_scene(self):
        accepted("(scene s (circle c (r 1))) (real v c.r) (readout ro f'{c.r}')")

    def test_every_expression_may_read_a_formula(self):
        accepted("(formula f $'\\term{a}{x}' (term a (fill #'red'))) (color|none v f.a.fill)")

    def test_a_view_or_a_control_may_read_a_control(self):
        accepted("(real size 1) " + SLIDER + " (readout ro f'{sz.position}')")
        accepted(
            "(real size 1) " + SLIDER + " (real k 0)"
            " (button b (animation (move k (to 1) (duration 1))) (active (> sz.position 1)))"
        )

    def test_the_scene_may_not_read_a_control(self):
        compile_error("(real size 1) " + SLIDER + " (scene s (circle c (r sz.position)))")

    @PAGE_READ
    def test_a_variable_at_the_top_level_may_not_read_a_control(self):
        compile_error("(real size 1) " + SLIDER + " (real r (if (> sz.position 2) 2 1))")
