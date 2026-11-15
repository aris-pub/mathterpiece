"""Conformance tests for docs/spec/evaluation.md.

What only the runtime can show is in web/test/conformance/evaluation.test.ts."""

from fractions import Fraction

import pytest

from .support import accepted, compile_error, is_bound, mtpc, obj, value

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


FOLDED_NONE = xfail("mtp-ydd4.7.48", "min, max, range and xs[i] reject a folded call")
PICK = xfail("mtp-ydd4.7.49", "pick always has a type that includes none")
NONE_ARGUMENT = xfail("mtp-ydd4.7.50", "a call folds its body with an argument that is none")
REVERSE = xfail("mtp-ydd4.7.51", "reverse of a known list that holds none raises TypeError")
NONE_COLLECTION = xfail("mtp-ydd4.7.52", "a collection that may be none is rejected")
WHOLE_FORMS = xfail("mtp-08wd.2", "cond, and and or are compiled whole")
COPIES = xfail("mtp-08wd.1", "each copy of a foreach is proved with the value of its variable")
RAND_BOUNDS = xfail("mtp-y7vp", "rand and rand-int do not check that lo is at most hi")
LIMIT = xfail("mtp-mqbu", "the compiler checks only literals against the number limit")
ROUND = xfail("mtp-6yga", "round of 10^28 or more raises decimal.InvalidOperation")
MIX = xfail("mtp-nk2w", "the compiler rounds the channels of a mixed color halves to even")
SEED_SIGN = xfail("mtp-ydd4.7.30", "the type rand-seed is an int of at least 0")
SITES = xfail("mtp-ydd4.7.39", "the compiler counts the sites in the order in which it compiles")
EQUAL_FUNCTIONS = xfail("mtp-08wd.4", "the compiler accepts = and != with every type")
DEPTH = xfail("mtp-ydd4.7.15", "a call is folded only to a depth of about 80")
ROUNDED = xfail("mtp-ydd4.7.38", "the functions on reals are not correctly rounded")

# f gives none at 0, and its body is proved once, for every real x.
INVERSE = "(func f ((real x)) (/ 1 x))\n"


@rule("evaluation-is-pure")
class TestEvaluationIsPure:
    def test_reading_a_value_changes_nothing(self):
        d = mtpc("(real a 1) (real b (+ a 1)) (real c (+ a 1))")
        assert obj(d, "a")["value"]["free"] == 1
        assert obj(d, "b")["value"]["bound"] == obj(d, "c")["value"]["bound"]

    def test_a_folded_call_changes_no_variable(self):
        d = mtpc("(real a 1) (func f ((real x)) (* 2 x)) (real v (f 3))")
        assert obj(d, "a")["value"]["free"] == 1
        assert obj(d, "v")["value"]["free"] == 6


@rule("arguments-before-call")
class TestArgumentsBeforeCall:
    def test_an_argument_that_the_body_does_not_read_is_evaluated(self):
        # g never reads a, but (/ 1 x) is evaluated, and when it gives none the call gives none.
        src = "(real x 0 (>= -1) (<= 1)) (func g ((real a) (real b)) b)"
        compile_error(src + " (real v (g (/ 1 x) 2))")
        accepted(src + " (real|none v (g (/ 1 x) 2))")


@rule("forms-evaluate-some-parts")
class TestFormsEvaluateSomeParts:
    def test_if_evaluates_only_the_branch_taken(self):
        assert value(INVERSE + "(real v (if (= 1 1) 3 (f 0)))", "v") == 3

    def test_or_default_evaluates_the_default_only_for_none(self):
        assert value(INVERSE + "(real v (or? (f 0) 5))", "v") == 5
        assert value(INVERSE + "(real v (or? (f 2) 5))", "v") == Fraction(1, 2)

    def test_a_let_value_that_nothing_reads_is_not_evaluated(self):
        # u would be none at x = 0, but nothing reads it, so v is 0 and not none.
        assert value("(real x 0 (>= -1) (<= 1)) (real v (let ((u (/ 1 x))) 0))", "v") == 0

    def test_fn_evaluates_nothing_until_it_is_called(self):
        src = "(func[real] g ((func[real real] h)) (h 2))"
        assert value(src + " (real v (g (fn ((real x)) (* x 3))))", "v") == 6


@rule("known-condition-takes-one-branch")
class TestKnownConditionTakesOneBranch:
    X = "(real x 0 (const))\n"

    def test_if(self):
        assert value(self.X + "(real a (if (= x 0) 0 (/ 1 x)))", "a") == 0

    @WHOLE_FORMS
    def test_cond(self):
        assert value(self.X + "(real b (cond ((= x 0) 0) (else (/ 1 x))))", "b") == 0

    @WHOLE_FORMS
    def test_and(self):
        assert value(self.X + "(bool c (and (> x 0) (> (/ 1 x) 2)))", "c") is False

    def test_let_is_proved_whole(self):
        compile_error(self.X + "(real d (let ((u (/ 1 x))) 0))")

    def test_or_default_is_proved_whole(self):
        compile_error("(real v (or? 2 (/ 1 0)))")

    def test_the_branch_not_taken_is_not_proved(self):
        assert value(self.X + "(real e (if (= x 0) 0 'not a number'))", "e") == 0

    def test_in_a_foreach_both_branches_are_proved(self):
        compile_error("(scene s (foreach i 2 (circle_ (r (if (= i 0) 1 'a')))))")


GIVES_NONE = [
    ("(/ 1 x)", "real", "0"),
    ("(mod 1 x)", "real", "0"),
    ("(^ x -1)", "real", "0"),
    ("(^ x 0.5)", "real", "-2"),
    ("(sqrt x)", "real", "-1"),
    ("(log x)", "real", "0"),
    ("(log x 2)", "real", "-1"),
    ("(log 2 x)", "real", "1"),
    ("(log 2 x)", "real", "0"),
    ("(tand x)", "real", "90"),
    ("(tand x)", "real", "-270"),
    ("(secd x)", "real", "90"),
    ("(cscd x)", "real", "180"),
    ("(cotd x)", "real", "0"),
    ("(csc x)", "real", "0"),
    ("(cot x)", "real", "0"),
    ("(asin x)", "real", "1.5"),
    ("(acos x)", "real", "-2"),
    ("(asind x)", "real", "2"),
    ("(acosd x)", "real", "2"),
    ("(asec x)", "real", "0.5"),
    ("(acsc x)", "real", "0"),
    ("(asecd x)", "real", "-0.5"),
    ("(acscd x)", "real", "0.9"),
    ("(to-polar [x 0])", "real", "0"),
    ("(range 0 1 (gap x))", "real", "0"),
    ("(range 0 1 (num x))", "int", "-1"),
    ("(* x x x)", "real", "1e150"),
]
GIVES_NONE_FOLD_REJECTS = [
    ("(min x)", "list[real]", "(as list[real] [])"),
    ("(max x)", "list[real]", "(as list[real] [])"),
    ("(range 0 x (gap 1))", "int", "2000000"),
    ("(. [1 2 3] x)", "int", "3"),
    ("(. [1 2 3] x)", "int", "-4"),
]


@rule("operations-that-give-none")
class TestOperationsThatGiveNone:
    @pytest.mark.parametrize("body, t, arg", GIVES_NONE)
    def test_a_folded_call_gives_none(self, body, t, arg):
        assert value(f"(func f (({t} x)) {body}) (bool v (none? (f {arg})))", "v") is True

    @FOLDED_NONE
    @pytest.mark.parametrize("body, t, arg", GIVES_NONE_FOLD_REJECTS)
    def test_a_folded_call_gives_none_and_is_not_rejected(self, body, t, arg):
        # Today the compiler rejects the call, as if its inputs were known in the prove step.
        assert value(f"(func f (({t} x)) {body}) (bool v (none? (f {arg})))", "v") is True

    @pytest.mark.parametrize(
        "body, t, arg",
        [
            ("(. [1 2 3] x)", "int", "-3"),
            ("(. [1 2 3] x)", "int", "2"),
            ("(tand x)", "real", "45"),
            ("(sqrt x)", "real", "0"),
            ("(asin x)", "real", "1"),
            ("(asec x)", "real", "1"),
            ("(log 2 x)", "real", "2"),
            ("(min x)", "list[real]", "[1]"),
        ],
    )
    def test_at_every_other_input_there_is_a_value(self, body, t, arg):
        assert value(f"(func f (({t} x)) {body}) (bool v (none? (f {arg})))", "v") is False

    @PICK
    def test_pick_on_a_list_that_is_not_empty_never_gives_none(self):
        accepted("(rand-seed sd 1) (real v (pick [1 2]))")

    def test_a_bound_value_that_may_break_its_constraint(self):
        m = accepted("(real k 1 (>= 0) (<= 2)) (real|none v (* 2 k) (<= 3))")
        assert m.get("v").value.expr.op == "check"


@rule("none-at-known-inputs")
class TestNoneAtKnownInputs:
    @pytest.mark.parametrize(
        "src",
        [
            "(real v (sqrt -1))",
            "(real v (or? (sqrt -1) 0))",
            "(real v (/ 1 0))",
            "(scene s (group g (circle c (r 1)))) (real v (. (. g 5) r))",
            "(scene s (foreach i 3 (circle_ (r (/ 1 i)))))",
            "(func[real] f ((real x)) (/ 1 x))",
        ],
    )
    def test_compile_errors(self, src):
        compile_error(src)

    @RAND_BOUNDS
    @pytest.mark.parametrize(
        "src",
        [
            "(rand-seed sd 1) (int b (rand-int 10 3))",
            "(rand-seed sd 1) ((int (>= 3) (<= 5)) b (rand-int 5 3))",
        ],
    )
    def test_rand_with_known_bounds_in_the_wrong_order(self, src):
        compile_error(src)

    @COPIES
    def test_a_default_in_the_body_of_a_foreach(self):
        accepted("(scene s (foreach i 3 (circle_ (r (or? (/ 1 i) 1)))))")

    def test_a_folded_call_whose_body_gives_none(self):
        assert value(INVERSE + "(real|none v (f 0))", "v") is None

    def test_a_default_in_the_body_of_a_function(self):
        src = "(func[real] f ((real t)) (let ((b (or? (sqrt t) 0))) (if (> t 0) b 1)))"
        assert value(src + " (real v (f -1))", "v") == 1


@rule("none-propagates")
class TestNonePropagates:
    def test_an_operation_on_none_gives_none(self):
        assert value("(func f ((real|none x)) (+ x 1)) (real|none v (f none))", "v") is None

    def test_or_default_gives_a_value_for_none(self):
        assert value(INVERSE + "(real v (or? (f 0) 5))", "v") == 5

    def test_equality_with_none(self):
        assert value(INVERSE + "(bool v (= (f 0) none))", "v") is True

    def test_a_parameter_that_allows_none(self):
        assert value("(func g ((real|none x)) (or? x 5)) (real v (g none))", "v") == 5

    @NONE_ARGUMENT
    def test_a_parameter_that_does_not_allow_none(self):
        # Today the body is evaluated, and the call gives 5.
        assert value(INVERSE + "(func h ((real x)) 5) (real|none v (h (f 0)))", "v") is None

    def test_a_list_holds_none(self):
        assert value(INVERSE + "(list[real|none] v [1 (f 0)])", "v") == [1, None]

    def test_a_point_with_a_coordinate_that_is_none_is_none(self):
        assert value(INVERSE + "(point|none v [1 (f 0)])", "v") is None

    def test_if_is_none_only_when_the_branch_taken_is(self):
        assert value(INVERSE + "(real|none v (if (= 1 1) 3 (f 0)))", "v") == 3
        assert value(INVERSE + "(real|none v (if (= 1 2) 3 (f 0)))", "v") is None

    def test_map_passes_none_through(self):
        assert value(INVERSE + "(list[real|none] v (map [1 0] f))", "v") == [1, None]

    @REVERSE
    def test_reverse_passes_none_through(self):
        # Today the compiler stops with a Python TypeError.
        assert value(INVERSE + "(list[real|none] v (reverse [1 (f 0)]))", "v") == [None, 1]

    def test_a_read_of_a_position_passes_none_through(self):
        assert value(INVERSE + "(real|none v (. [1 (f 0)] 1))", "v") is None

    def test_a_part_of_none_is_none(self):
        assert value("(func p ((real x)) [(/ 1 x) 0]) (real|none v (. (p 0) 0))", "v") is None

    def test_an_interpolated_string_with_a_part_that_is_none(self):
        assert value(INVERSE + "(string|none v $'a{(f 0)}')", "v") is None

    @NONE_COLLECTION
    def test_a_collection_function_given_none(self):
        src = "(list[int]|none v (map (if (= 1 2) [1] none) (fn ((int x)) x)))"
        assert value(src, "v") is None


@rule("none-never-a-condition")
class TestNoneNeverACondition:
    def test_the_condition_of_an_if(self):
        compile_error("(bool|none c none) (real v (if c 1 2))")

    def test_active(self):
        compile_error(
            "(bool|none c none) (real k 0)"
            " (button b (active c) (animation (move k (to 1) (duration 1))))"
        )

    @pytest.mark.parametrize("f", ["sum", "min", "max", "count"])
    def test_the_items_of_a_collection_function(self, f):
        compile_error(INVERSE + f"(real v ({f} [1 (f 0)]))")


@rule("number-types")
class TestNumberTypes:
    def test_an_int_is_exact(self):
        assert value("(int v (+ (^ 2 60) 1))", "v") == 2**60 + 1

    def test_a_ratio_is_exact(self):
        assert value("(ratio v (+ (/ 1 10) 1/5))", "v") == Fraction(3, 10)

    def test_the_mtpc_writes_a_ratio_in_lowest_terms(self):
        d = mtpc("(ratio v 2/4)")
        assert obj(d, "v")["value"]["free"] == [1, 2]

    def test_a_real_is_a_double(self):
        assert value("(real v (+ 0.1 0.2))", "v") == 0.1 + 0.2

    def test_a_complex_is_two_doubles(self):
        assert value("(complex v (* 1+2i 2))", "v") == complex(2, 4)


@rule("number-result-types")
class TestNumberResultTypes:
    @pytest.mark.parametrize(
        "expr, kind",
        [
            ("(+ 1 2)", "int"),
            ("(+ 1 1/2)", "ratio"),
            ("(+ 1 0.5)", "real"),
            ("(+ 1/2 0.5)", "real"),
            ("(+ 1 1i)", "complex"),
            ("(/ 1 2)", "ratio"),
            ("(^ 2 3)", "int"),
            ("(^ 2 -1)", "ratio"),
            ("(^ 2 0.5)", "real"),
            ("(^ 2 1i)", "complex"),
            ("(abs 3+4i)", "real"),
        ],
    )
    def test_the_type_of_a_result(self, expr, kind):
        assert value(f"(string v (type-of {expr}))", "v") == kind

    def test_a_power_whose_range_holds_a_negative_int(self):
        assert value("(int n 2 (>= 0) (<= 4)) (string v (type-of (^ 2 n)))", "v") == "int"
        assert value("(int n 2 (>= -1) (<= 4)) (string v (type-of (^ 2 n)))", "v") == "ratio"

    def test_an_int_is_converted_to_the_nearest_real_ties_to_even(self):
        assert value("(real v (+ 9007199254740993 0.0))", "v") == 9007199254740992.0
        assert value("(real v (+ 9007199254740995 0.0))", "v") == 9007199254740996.0


@rule("number-limit")
class TestNumberLimit:
    @pytest.mark.parametrize("lit", ["1e151", "-1e151", "1" + "0" * 151])
    def test_a_literal_beyond_the_limit(self, lit):
        compile_error(f"(real v {lit})")

    def test_a_literal_at_the_limit(self):
        accepted("(real v 1e150)")

    @LIMIT
    def test_a_free_starting_value_beyond_the_limit(self):
        compile_error("(real k free@(* 1e100 1e100))")

    @LIMIT
    def test_a_starting_value_known_when_compiling_beyond_the_limit(self):
        compile_error("(real k (* 1e100 1e100))")

    def test_a_computed_result_is_not_held_to_the_limit(self):
        assert value("(func f ((real x)) (* x x)) (real v (f 1e100))", "v") == 1e200


@rule("rounding")
class TestRounding:
    @pytest.mark.parametrize(
        "x, r", [("2.5", 3), ("-2.5", -3), ("0.5", 1), ("1.4", 1), ("-0.5", -1)]
    )
    def test_round_halves_away_from_zero(self, x, r):
        assert value(f"(int v (round {x}))", "v") == r

    def test_round_to_decimal_places_on_the_shortest_decimal_form(self):
        assert value("(real v (round 0.125 2))", "v") == 0.13
        assert value("(real v (round 2.675 2))", "v") == 2.68

    def test_a_format_spec(self):
        assert value("(string v $'{0.125:.2f} {2.675:.2f} {2.5:.0f}')", "v") == "0.13 2.68 3"

    @ROUND
    def test_round_gives_none_at_no_input(self):
        assert value("(real v (round 1e28))", "v") == 1e28


@rule("mixed-color-channels")
class TestMixedColorChannels:
    @MIX
    def test_a_channel_that_lies_halfway_rounds_up(self):
        assert value("(color v (mix '#000000' '#050505' 0.5))", "v") == "#030303ff"

    def test_a_channel_that_does_not_lie_halfway(self):
        assert value("(color v (mix '#000000' '#060606' 0.5))", "v") == "#030303ff"


@rule("seed-variable")
class TestSeedVariable:
    def test_a_random_function_follows_its_seed(self):
        m = accepted("(rand-seed a 1) (rand-seed b 2) (real v (rand 0 1 (seed b)))")
        assert (m.id("b"), None) in m.get("v").value.deps
        assert (m.id("a"), None) not in m.get("v").value.deps

    def test_a_const_variable_is_not_a_seed(self):
        compile_error("(rand-seed s 3 (const)) (real v (rand))")

    @SEED_SIGN
    def test_a_seed_is_any_int(self):
        accepted("(rand-seed s -1) (real v (rand))")

    def test_with_several_seeds_a_random_function_names_one(self):
        compile_error("(rand-seed a 1) (rand-seed b 2) (real v (rand))")


def _sites(d: dict) -> dict:
    """The site of each random variable of a .mtpc, by name."""
    found = {}
    for o in d["objects"]:
        bound = o.get("value", {}).get("bound")
        if bound and bound[0] in ("rand", "rand-int", "pick", "shuffle"):
            found[o["name"]] = bound[2]
    return found


@rule("random-site")
class TestRandomSite:
    def test_sites_count_from_0_in_the_order_of_the_text(self):
        d = mtpc("(rand-seed s 1) (real a (rand)) (real b (rand)) (int c (rand-int 1 6))")
        assert _sites(d) == {"a": 0, "b": 1, "c": 2}

    def test_each_copy_of_a_foreach_has_its_own_site(self):
        d = mtpc("(rand-seed s 1) (foreach i 3 (real #'k-{i}' (rand)))")
        assert _sites(d) == {"k-0": 0, "k-1": 1, "k-2": 2}

    @SITES
    def test_the_order_in_which_the_attributes_of_a_shape_are_written(self):
        d = mtpc("(rand-seed sd 1) (scene s (circle c (r (rand 1 2)) (x (rand 0 5))))")
        c = obj(d, "c")["attrs"]
        assert (c["r"]["bound"][2], c["x"]["bound"][2]) == (0, 1)

    def test_a_call_in_the_arguments_of_another_call_comes_after_it(self):
        d = mtpc("(rand-seed sd 1) (real v (rand (rand 0 1) 5))")
        outer = obj(d, "v")["value"]["bound"]
        inner = outer[4] if outer[4][0] == "rand" else outer[3]
        assert outer[2] == 0 and inner[2] == 1


@rule("random-never-folded")
class TestRandomNeverFolded:
    @pytest.mark.parametrize(
        "src",
        [
            "(rand-seed s 1) (real v (rand))",
            "(rand-seed s 1) (int v (rand-int 1 6))",
            "(rand-seed s 1) (real|none v (pick (as list[real] [1 2])))",
            "(rand-seed s 1) (list[int] v (shuffle [1 2 3]))",
        ],
    )
    def test_a_random_value_is_known_only_while_drawing(self, src):
        assert is_bound(src, "v")


@rule("equality-operands")
class TestEqualityOperands:
    def test_a_point_and_a_list_of_ints(self):
        compile_error("(point p [1 2] (const)) (list[int] xs [1 2] (const)) (bool v (= p xs))")

    def test_a_literal_list_takes_the_type_of_the_other_side(self):
        assert value("(point p [1 2] (const)) (bool v (= p [1 2]))", "v") is True

    def test_two_types_that_do_not_fit(self):
        compile_error("(bool v (= 1 'a'))")

    def test_one_side_is_none(self):
        accepted("(real k 1) (bool v (= k none))")

    @EQUAL_FUNCTIONS
    @pytest.mark.parametrize(
        "src",
        [
            "(bool v (= sind sind))",
            "(real k 0) (transition t k (to 1) (duration 1)) (bool v (= t t))",
            "(bool v (!= [sind] [cosd]))",
        ],
    )
    def test_functions_transitions_and_animations(self, src):
        compile_error(src)


@rule("equality-by-content")
class TestEqualityByContent:
    @pytest.mark.parametrize(
        "a, b, result",
        [
            ("0", "-0.0", True),
            ("1", "1.0", True),
            ("1/2", "0.5", True),
            ("1+0i", "1.0", True),
            ("1+2i", "1+2i", True),
            ("(+ 0.1 0.2)", "0.3", False),
            ("'a'", "'a'", True),
            ("'a'", "'A'", False),
            ("true", "true", True),
            ("[1 2]", "[1 2]", True),
            ("[1 2]", "[1 2 3]", False),
            ("(as point [1 2])", "(as point [1 2])", True),
            ("(as color 'navy')", "(as color '#000080')", True),
        ],
    )
    def test_values_compare_by_content(self, a, b, result):
        assert value(f"(bool v (= {a} {b}))", "v") is result
        assert value(f"(bool v (!= {a} {b}))", "v") is (not result)

    def test_none_equals_only_none(self):
        assert value(INVERSE + "(bool v (= (f 0) (f 0)))", "v") is True
        assert value(INVERSE + "(bool v (= (f 0) 1))", "v") is False


@rule("call-depth-limit")
class TestCallDepthLimit:
    DOWN = "(func[int] down ((int m)) (if (<= m 0) 0 (+ 1 (down (- m 1)))))\n"

    def test_a_short_chain_is_folded(self):
        assert value(self.DOWN + "(int v (down 10))", "v") == 10

    @DEPTH
    def test_a_chain_of_depth_256_is_folded(self):
        assert value(self.DOWN + "(int v (down 255))", "v") == 255

    @DEPTH
    def test_a_chain_deeper_than_256_is_a_compile_error(self):
        compile_error(self.DOWN + "(int v (down 256))")


@rule("correctly-rounded-reals")
class TestCorrectlyRoundedReals:
    @pytest.mark.parametrize(
        "expr, exact",
        [("(+ 0.1 0.2)", 0.30000000000000004), ("(sqrt 2)", 2**0.5), ("(/ 1 3.0)", 1 / 3)],
    )
    def test_the_basic_operations(self, expr, exact):
        assert value(f"(real v {expr})", "v") == exact

    @ROUNDED
    @pytest.mark.parametrize("expr, exact", [("(sind 30)", 0.5), ("(cosd 60)", 0.5)])
    def test_the_functions_in_degrees(self, expr, exact):
        assert value(f"(real v {expr})", "v") == exact

    def test_sum_rounds_once(self):
        # The exact sum of the three doubles rounds to 0.6, while adding them one at a time gives
        # 0.6000000000000001.
        assert value("(real v (sum [0.1 0.2 0.3]))", "v") == 0.6
