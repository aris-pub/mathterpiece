"""Conformance tests of the rule known-when-compiling (docs/spec/binding-time.md)."""

from ._shared import OBJECT_ARGUMENT, RANDOM_NAMES, free, is_bound, mtpc, obj, rule, value


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
