"""Conformance tests for docs/spec/evaluation.md.

What only the runtime can show is in web/test/conformance/evaluation.test.ts."""

from fractions import Fraction

import pytest

from .support import accepted, compile_error, in_folder, is_bound, mtpc, obj, same_meaning, value

RAND = "(import rand rand rand-int pick shuffle next-seed roll-dice) "

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
]
GIVES_NONE_FOLD_REJECTS = [
    ("(min x)", "list[real]", "(as list[real] {})"),
    ("(max x)", "list[real]", "(as list[real] {})"),
    ("(range 0 x (gap 1))", "int", "2000000"),
    ("(. {1 2 3} x)", "int", "3"),
    ("(. {1 2 3} x)", "int", "-4"),
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
            ("(. {1 2 3} x)", "int", "-3"),
            ("(. {1 2 3} x)", "int", "2"),
            ("(tand x)", "real", "45"),
            ("(sqrt x)", "real", "0"),
            ("(asin x)", "real", "1"),
            ("(asec x)", "real", "1"),
            ("(log 2 x)", "real", "2"),
            ("(min x)", "list[real]", "{1}"),
        ],
    )
    def test_at_every_other_input_there_is_a_value(self, body, t, arg):
        assert value(f"(func f (({t} x)) {body}) (bool v (none? (f {arg})))", "v") is False

    def test_a_result_beyond_the_largest_real_is_not_none(self):
        assert value("(func f ((real x)) (* x x x)) (bool v (none? (f 1e150)))", "v") is False

    @pytest.mark.parametrize(
        "body, arg",
        [("(exp x)", "1000"), ("(^ x 400)", "10.0"), ("(/ 1 x)", "1e-200"), ("(csc x)", "1e-200")],
    )
    def test_an_overflow_is_not_none(self, body, arg):
        assert value(f"(func f ((real x)) {body}) (bool v (none? (f {arg})))", "v") is False

    @pytest.mark.parametrize("src", ["(real k 1) (real v (exp k))", "(real k 1) (real v (^ 2 k))"])
    def test_a_result_that_may_overflow_is_never_none(self, src):
        accepted(src)

    @PICK
    def test_pick_on_a_list_that_is_not_empty_never_gives_none(self):
        accepted(RAND + "(rand-seed sd 1) (real v (pick {1 2}))")

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
            RAND + "(rand-seed sd 1) (int b (rand-int 10 3))",
            RAND + "(rand-seed sd 1) ((int (>= 3) (<= 5)) b (rand-int 5 3))",
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
        assert value(INVERSE + "(list[real|none] v {1 (f 0)})", "v") == [1, None]

    def test_a_point_with_a_coordinate_that_is_none_is_none(self):
        assert value(INVERSE + "(point|none v [1 (f 0)])", "v") is None

    def test_if_is_none_only_when_the_branch_taken_is(self):
        assert value(INVERSE + "(real|none v (if (= 1 1) 3 (f 0)))", "v") == 3
        assert value(INVERSE + "(real|none v (if (= 1 2) 3 (f 0)))", "v") is None

    def test_map_passes_none_through(self):
        assert value(INVERSE + "(list[real|none] v (map {1 0} f))", "v") == [1, None]

    @REVERSE
    def test_reverse_passes_none_through(self):
        # Today the compiler stops with a Python TypeError.
        assert value(INVERSE + "(list[real|none] v (reverse {1 (f 0)}))", "v") == [None, 1]

    def test_a_read_of_a_position_passes_none_through(self):
        assert value(INVERSE + "(real|none v (. {1 (f 0)} 1))", "v") is None

    def test_a_part_of_none_is_none(self):
        assert value("(func p ((real x)) {(/ 1 x) 0}) (real|none v (. (p 0) 0))", "v") is None

    def test_an_interpolated_string_with_a_part_that_is_none(self):
        assert value(INVERSE + "(string|none v f'a{(f 0)}')", "v") is None

    @NONE_COLLECTION
    def test_a_collection_function_given_none(self):
        src = "(list[int]|none v (map (if (= 1 2) {1} none) (fn ((int x)) x)))"
        assert value(src, "v") is None


@rule("none-never-a-condition")
class TestNoneNeverACondition:
    def test_the_condition_of_an_if(self):
        compile_error("(bool|none c none) (real v (if c 1 2))")

    def test_active(self):
        compile_error(
            "(bool|none c none) (real k 0) (button b (move k (to 1) (duration 1)) (active c))"
        )

    @pytest.mark.parametrize("f", ["sum", "min", "max", "count"])
    def test_the_items_of_a_collection_function(self, f):
        compile_error(INVERSE + f"(real v ({f} {{1 (f 0)}}))")


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

    def test_a_real_is_finite_so_there_is_no_constant_for_infinity(self):
        compile_error("(real v infty)")


@rule("point-arithmetic")
class TestPointArithmetic:
    def test_points_add_coordinate_by_coordinate(self):
        assert value("(point v (+ [1 2] [3 4]))", "v") == (4, 6)

    def test_a_point_times_a_real(self):
        assert value("(point v (* 2 [1 2]))", "v") == (2, 4)

    @xfail("mtp-5ir0", "no point-of, and no division of a point")
    def test_the_zero_and_the_other_operations(self):
        assert value("(point v (- (/ [2 4] 2) (point-of 0 0)))", "v") == (1, 2)
        assert value("(point v (- [1 2]))", "v") == (-1, -2)


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
        accepted("(int v -1" + "0" * 150 + ")")

    @pytest.mark.parametrize(
        "expr, limit",
        [("(f 1e100)", 1e150), ("(f -1e100)", 1e150), ("(- (f 1e100))", -1e150)],
    )
    def test_a_real_result_is_clamped(self, expr, limit):
        assert value(f"(func f ((real x)) (* x x)) (real v {expr})", "v") == limit

    def test_a_result_beyond_the_largest_real_is_clamped(self):
        assert value("(real v (* 1e150 1e150 1e150))", "v") == 1e150

    def test_an_int_result_is_clamped_to_exactly_the_limit(self):
        assert value("(int v (* (^ 10 100) (^ 10 100)))", "v") == 10**150

    def test_a_ratio_result_is_clamped_to_exactly_the_limit(self):
        assert value("(ratio v (* (/ (^ 10 100) 3) (^ 10 100)))", "v") == 10**150

    def test_each_operation_is_clamped_on_its_own(self):
        # (^ 10 200) is clamped to 10^150 before it is divided.
        assert value("(ratio v (/ (^ 10 200) 3))", "v") == Fraction(10**150, 3)

    def test_an_int_inside_the_limit_stays_exact(self):
        assert value("(int v (+ (^ 10 149) 1))", "v") == 10**149 + 1

    def test_an_operation_with_several_arguments_is_clamped_once(self):
        # Clamped after each product, the value would be 1e-50.
        assert value("(real v (* 1e150 1e150 1e-200))", "v") == pytest.approx(1e100)

    def test_a_starting_value_known_when_compiling_is_clamped(self):
        assert value("(real k (* 1e100 1e100))", "k") == 1e150

    def test_a_free_starting_value_is_clamped(self):
        assert obj(mtpc("(real k free@(* 1e100 1e100))"), "k")["value"]["free"] == 1e150

    def test_a_product_past_the_largest_binary64_number_is_clamped_once(self):
        # The product of the first three is past the largest binary64 number, and the exact
        # product of the four is 1e140.
        v = value("(real v (* 1e150 1e150 1e150 1e-310))", "v")
        assert v == pytest.approx(1e140)

    @pytest.mark.parametrize(
        "expr, limit",
        [
            ("(+ 1e150 1e150)", 1e150),
            ("(- -1e150 1e150)", -1e150),
            ("(/ 1 1e-200)", 1e150),
            ("(/ -1e150 1e-10)", -1e150),
            ("(^ 10.0 400)", 1e150),
            ("(^ -10.0 401)", -1e150),
            ("(^ 1e150 1.5)", 1e150),
            ("(sum {1e150 1e150})", 1e150),
            ("(abs 1e150+1e150i)", 1e150),
        ],
    )
    def test_each_operation_is_clamped(self, expr, limit):
        assert value(f"(real v {expr})", "v") == limit

    @pytest.mark.parametrize(
        "expr, limit",
        [
            ("(exp 1000)", 1e150),
            ("(rad 1e150)", 1e150),
            ("(turn -1e150)", -1e150),
            ("(dist [-1e150 0] [1e150 0])", 1e150),
            ("(lerp 0 1e150 1e150)", 1e150),
        ],
    )
    def test_each_built_in_function_is_clamped(self, expr, limit):
        assert value(f"(real v {expr})", "v") == limit

    def test_an_exact_power_is_clamped_to_exactly_the_limit(self):
        assert value("(int v (^ 10 1000))", "v") == 10**150
        assert value("(int v (^ -10 1001))", "v") == -(10**150)

    def test_a_power_with_a_very_large_exponent(self):
        # The exact value has more than 10^100 digits, so it is never worked out.
        assert value("(int v (^ 2 (^ 10 100)))", "v") == 10**150
        assert value("(int v (^ -3 (+ (^ 10 100) 1)))", "v") == -(10**150)

    def test_each_part_of_a_complex_is_clamped(self):
        assert value("(complex v (* 1e100+1e100i 1e100))", "v") == complex(1e150, 1e150)
        assert value("(complex v (^ 1e150+0i 3))", "v") == complex(1e150, 0)

    def test_each_number_of_a_point_or_a_list_is_clamped(self):
        assert value("(point v (* [1e100 -1e100] 1e100))", "v") == (1e150, -1e150)
        assert value("(list[real] v (+ {1e150 1} {1e150 1}))", "v") == [1e150, 2]
        assert value("(point v (polar 1e150 45))", "v") == pytest.approx(
            (1e150 / 2**0.5, 1e150 / 2**0.5)
        )

    def test_a_product_of_ints_with_no_bounds_is_an_int(self):
        accepted("(int n 1) (int v (* n n n))")


@rule("range-rules")
class TestRangesAreClamped:
    @pytest.mark.parametrize(
        "src",
        [
            "(real k 1) (real v (* k k) (<= 1e150))",
            "(real k 1) (real v (* k k k) (>= -1e150))",
            "(real k 1) (real v (^ 2 k) (<= 1e150))",
            "(real k 1) (real v (exp k) (<= 1e150))",
            "(real k 2 (> 0)) (real h (/ 1 k) (<= 1e150))",
            "(real k -2 (< 0)) (real h (/ 1 k) (>= -1e150))",
            "(real k 1 (>= 1e-300)) (real h (* (/ 1 k) (/ 1 k)) (<= 1e150))",
        ],
    )
    def test_a_range_never_passes_the_number_limit(self, src):
        accepted(src)

    def test_a_range_past_the_largest_binary64_number_gives_no_none(self):
        accepted("(real k 2 (> 0)) (real h (/ 1 k))")
        accepted("(real a) (real b) (real c) (real d (* a b c))")

    def test_a_pole_still_gives_none(self):
        compile_error("(real k 2 (>= 0)) (real h (/ 1 k))")
        compile_error("(real k 1 (>= 0) (<= 180)) (real h (tand k))")


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
        assert value("(string v f'{0.125:.2f} {2.675:.2f} {2.5:.0f}')", "v") == "0.13 2.68 3"

    @ROUND
    def test_round_gives_none_at_no_input(self):
        assert value("(real v (round 1e28))", "v") == 1e28


@rule("mixed-color-channels")
class TestMixedColorChannels:
    @MIX
    def test_a_channel_that_lies_halfway_rounds_up(self):
        assert value("(color v (mix #'#000000' #'#050505' 0.5))", "v") == "#030303ff"

    def test_a_channel_that_does_not_lie_halfway(self):
        assert value("(color v (mix #'#000000' #'#060606' 0.5))", "v") == "#030303ff"


@rule("seed-variable")
class TestSeedVariable:
    def test_a_random_function_follows_its_seed(self):
        m = accepted(RAND + "(rand-seed a 1) (rand-seed b 2) (real v (rand 0 1 (seed b)))")
        assert (m.id("b"), None) in m.get("v").value.deps
        assert (m.id("a"), None) not in m.get("v").value.deps

    def test_a_const_variable_is_not_a_seed(self):
        compile_error(RAND + "(rand-seed s 3 (const)) (real v (rand))")

    @SEED_SIGN
    def test_a_seed_is_any_int(self):
        accepted(RAND + "(rand-seed s -1) (real v (rand))")

    def test_with_several_seeds_a_random_function_names_one(self):
        compile_error(RAND + "(rand-seed a 1) (rand-seed b 2) (real v (rand))")


@rule("default-seed")
class TestDefaultSeed:
    def test_the_only_seed_of_the_file_scope(self):
        m = accepted(RAND + "(rand-seed a 1) (real v (rand))")
        assert (m.id("a"), None) in m.get("v").value.deps

    def test_a_seed_that_an_import_gives(self, tmp_path):
        (tmp_path / "lib.mtp").write_text("(rand-seed hs 3)")
        m = accepted(RAND + "(import lib hs) (real v (rand))", tmp_path / "a.mtp")
        assert (m.id("lib.hs"), None) in m.get("v").value.deps

    def test_with_no_variable_of_type_rand_seed_the_seed_of_rand(self):
        m = accepted(RAND + "(real v (rand))")
        assert (m.id("rand.seed"), None) in m.get("v").value.deps

    def test_a_const_variable_of_type_rand_seed_is_not_a_seed(self):
        compile_error(RAND + "(rand-seed s 3 (const)) (real v (rand))")
        m = accepted(RAND + "(rand-seed s 3 (const)) (rand-seed t 4) (real v (rand))")
        assert (m.id("t"), None) in m.get("v").value.deps

    def test_a_seed_declared_after_the_use(self):
        compile_error(RAND + "(real v (rand)) (rand-seed a 1)")

    def test_several_seeds(self):
        compile_error(RAND + "(rand-seed a 1) (rand-seed b 2) (real v (rand))")

    def test_the_seed_of_rand_and_another(self, tmp_path):
        compile_error("(import rand) (rand-seed a 1) (real v (rand.rand))", tmp_path / "a.mtp")

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
            RAND + "(rand-seed s 1) (button b (roll-dice))",
            RAND + "(rand-seed s 1) (button b (roll-dice s))",
        )

    def test_roll_dice_with_no_seed_by_the_name_of_the_file(self, tmp_path):
        same_meaning(
            "(import rand) (button b (rand.roll-dice))",
            "(import rand) (button b (rand.roll-dice rand.seed))",
            tmp_path / "a.mtp",
        )

    def test_roll_dice_is_its_choreo(self):
        same_meaning(
            RAND + "(rand-seed s 1) (button b (roll-dice s))",
            RAND + "(rand-seed s 1) (button b (set s (next-seed s)))",
        )

    def test_roll_dice_needs_a_seed(self):
        compile_error(RAND + "(real k 1) (button b (roll-dice k))")

    def test_roll_dice_with_several_seeds(self):
        compile_error(RAND + "(rand-seed s 1) (rand-seed t 2) (button b (roll-dice))")


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
        d = mtpc(RAND + "(rand-seed s 1) (real a (rand)) (real b (rand)) (int c (rand-int 1 6))")
        assert _sites(d) == {"a": 0, "b": 1, "c": 2}

    def test_each_copy_of_a_foreach_has_its_own_site(self):
        d = mtpc(RAND + "(rand-seed s 1) (foreach i 3 (real @'k-{i}' (rand)))")
        assert _sites(d) == {"k-0": 0, "k-1": 1, "k-2": 2}

    @SITES
    def test_the_order_in_which_the_attributes_of_a_shape_are_written(self):
        d = mtpc(RAND + "(rand-seed sd 1) (scene s (circle c (r (rand 1 2)) (x (rand 0 5))))")
        c = obj(d, "c")["attrs"]
        assert (c["r"]["bound"][2], c["x"]["bound"][2]) == (0, 1)

    def test_a_call_in_the_arguments_of_another_call_comes_after_it(self):
        d = mtpc(RAND + "(rand-seed sd 1) (real v (rand (rand 0 1) 5))")
        outer = obj(d, "v")["value"]["bound"]
        inner = outer[4] if outer[4][0] == "rand" else outer[3]
        assert outer[2] == 0 and inner[2] == 1


@rule("random-never-folded")
class TestRandomNeverFolded:
    @pytest.mark.parametrize(
        "src",
        [
            RAND + "(rand-seed s 1) (real v (rand))",
            RAND + "(rand-seed s 1) (int v (rand-int 1 6))",
            RAND + "(rand-seed s 1) (real|none v (pick (as list[real] {1 2})))",
            RAND + "(rand-seed s 1) (list[int] v (shuffle {1 2 3}))",
        ],
    )
    def test_a_random_value_is_known_only_while_drawing(self, src):
        assert is_bound(src, "v")


@rule("equality-operands")
class TestEqualityOperands:
    def test_a_point_and_a_list_of_ints(self):
        compile_error("(point p [1 2] (const)) (list[int] xs {1 2} (const)) (bool v (= p xs))")

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
            "(bool v (!= {sind} {cosd}))",
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
            ("{1 2}", "{1 2}", True),
            ("{1 2}", "{1 2 3}", False),
            ("(as point [1 2])", "(as point [1 2])", True),
            ("(as color #'navy')", "(as color #'#000080')", True),
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
        assert value("(real v (sum {0.1 0.2 0.3}))", "v") == 0.6
