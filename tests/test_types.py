import pytest

from mathterpiece.nodes import Bar, Brackets, Form, IntLit, ListLit, Name, NoneLit, RealLit, StrLit
from mathterpiece.parse import parse
from mathterpiece.types import (
    BOOL,
    COLOR,
    COMPLEX,
    INT,
    NONE,
    POINT,
    RATIO,
    REAL,
    STRING,
    FuncT,
    Interface,
    ListT,
    Maybe,
    Refine,
    ShapeT,
    TypeError_,
    fits,
    literal_type,
    type_from_node,
)


def node(text):
    (form,) = parse(f"(f {text})")
    return form.items[1]


class TestNumbersBroaden:
    # type-system.md, section 3: int, ratio, real, complex, each accepted where a later one is.
    @pytest.mark.parametrize(
        "narrow, wide",
        [
            (INT, RATIO),
            (INT, REAL),
            (INT, COMPLEX),
            (RATIO, REAL),
            (RATIO, COMPLEX),
            (REAL, COMPLEX),
        ],
    )
    def test_broadens(self, narrow, wide):
        assert fits(narrow, wide)

    @pytest.mark.parametrize("wide, narrow", [(REAL, INT), (COMPLEX, REAL), (RATIO, INT)])
    def test_never_narrows(self, wide, narrow):
        assert not fits(wide, narrow)

    def test_a_type_fits_itself(self):
        for t in (INT, REAL, BOOL, STRING, COLOR, POINT, ListT(REAL)):
            assert fits(t, t)

    def test_unrelated_types_do_not_fit(self):
        assert not fits(STRING, COLOR)
        assert not fits(BOOL, INT)


class TestNone:
    def test_t_fits_t_or_none(self):
        assert fits(REAL, Maybe(REAL))
        assert fits(INT, Maybe(REAL))
        assert fits(NONE, Maybe(REAL))

    def test_t_or_none_does_not_fit_t(self):
        assert not fits(Maybe(REAL), REAL)


class TestLists:
    def test_a_narrower_list_fits_a_wider_one(self):
        # A list never changes, so every list of ints is a list of reals.
        assert fits(ListT(INT), ListT(REAL))
        assert not fits(ListT(REAL), ListT(INT))


class TestFunctions:
    def test_inputs_and_result(self):
        assert fits(FuncT((REAL,), REAL), FuncT((REAL,), REAL))
        assert not fits(FuncT((REAL,), REAL), FuncT((REAL, REAL), REAL))

    def test_a_function_taking_wider_inputs_and_giving_a_narrower_result_fits(self):
        assert fits(FuncT((REAL,), INT), FuncT((INT,), REAL))
        assert not fits(FuncT((INT,), REAL), FuncT((REAL,), REAL))


class TestShapes:
    def test_every_shape_satisfies_shape(self):
        for name in ("circle", "rect", "ellipse", "line", "triangle", "text", "group"):
            assert fits(ShapeT(name), Interface("shape"))

    def test_every_shape_but_groups_is_positioned(self):
        assert fits(ShapeT("circle"), Interface("positioned"))
        assert fits(POINT, Interface("positioned"))
        assert not fits(ShapeT("group"), Interface("positioned"))

    def test_shapes_are_not_each_other(self):
        assert not fits(ShapeT("rect"), ShapeT("circle"))


class TestLiterals:
    # A literal takes the type of its place (type-system.md, section 3).
    def test_numbers(self):
        assert literal_type(IntLit(3), None) == INT
        assert literal_type(RealLit(2.5), None) == REAL
        assert literal_type(IntLit(3), REAL) == REAL

    def test_a_string_is_a_color_where_a_color_is_expected(self):
        assert literal_type(StrLit("red"), None) == STRING
        assert literal_type(StrLit("red"), COLOR) == COLOR
        assert literal_type(StrLit("#ff000080"), COLOR) == COLOR

    def test_a_string_that_is_not_a_color(self):
        with pytest.raises(TypeError_, match="not a color"):
            literal_type(StrLit("blurple"), COLOR)

    def test_none(self):
        assert literal_type(NoneLit(), Maybe(REAL)) == Maybe(REAL)
        with pytest.raises(TypeError_):
            literal_type(NoneLit(), REAL)

    def test_lists_infer_their_item_type(self):
        assert literal_type(ListLit((IntLit(1), IntLit(2))), None) == ListT(INT)
        assert literal_type(ListLit((IntLit(1), RealLit(2.5))), None) == ListT(REAL)
        assert literal_type(ListLit((StrLit("red"),)), None) == ListT(STRING)

    def test_a_list_takes_its_place_type(self):
        assert literal_type(ListLit((StrLit("red"),)), ListT(COLOR)) == ListT(COLOR)
        assert literal_type(ListLit((IntLit(1), IntLit(2))), POINT) == POINT

    def test_a_point_needs_two_numbers(self):
        with pytest.raises(TypeError_, match="point"):
            literal_type(ListLit((IntLit(1),)), POINT)

    def test_an_empty_list_needs_its_place(self):
        assert literal_type(ListLit(()), ListT(REAL)) == ListT(REAL)
        with pytest.raises(TypeError_, match="empty list"):
            literal_type(ListLit(()), None)


class TestTypeNotation:
    @pytest.mark.parametrize(
        "text, t",
        [
            ("real", REAL),
            ("int", INT),
            ("color", COLOR),
            ("point", POINT),
            ("list[color]", ListT(COLOR)),
            ("list[list[real]]", ListT(ListT(REAL))),
            ("real|none", Maybe(REAL)),
            ("list[real|none]", ListT(Maybe(REAL))),
            ("(maybe real)", Maybe(REAL)),
            ("func[real real]", FuncT((REAL,), REAL)),
            ("func[real point real]", FuncT((REAL, POINT), REAL)),
            ("func[real]", FuncT((), REAL)),
            ("circle", ShapeT("circle")),
            ("shape", Interface("shape")),
            ("sequence[circle]", Interface("sequence", ShapeT("circle"))),
        ],
    )
    def test_types(self, text, t):
        assert type_from_node(node(text)) == t

    @pytest.mark.parametrize(
        "text, message",
        [
            ("blob", "unknown type 'blob'"),
            ("list", "list needs its item type"),
            ("list[a b]", "list takes one item type"),
            ("real[int]", "real takes no item type"),
            ("real|int", "only by none"),
        ],
    )
    def test_invalid(self, text, message):
        with pytest.raises(TypeError_, match=message):
            type_from_node(node(text))

    def test_the_nodes_it_reads(self):
        assert type_from_node(Bar((Name(("real",)), NoneLit()))) == Maybe(REAL)
        assert type_from_node(Name(("func", Brackets((Name(("real",)), Name(("real",))))))) == (
            FuncT((REAL,), REAL)
        )
        assert type_from_node(Form((Name(("maybe",)), Name(("real",))))) == Maybe(REAL)


class TestRefinement:
    # type-system.md, section 5.b.
    def test_a_narrowed_type_form(self):
        t = type_from_node(node("(real (>= 0) (<= 1))"))
        assert t == Refine(REAL, ((">=", 0), ("<=", 1)))

    def test_constraints(self):
        assert type_from_node(node("(list[real] (length 3))")) == Refine(
            ListT(REAL), (("length", 3),)
        )
        assert type_from_node(node("(string (one-of 'left' 'right'))")) == Refine(
            STRING, (("one-of", ("left", "right")),)
        )
        assert type_from_node(node("(int (const))")) == Refine(INT, (("const",),))

    def test_a_narrowed_type_fits_its_base(self):
        unit = Refine(REAL, ((">=", 0), ("<=", 1)))
        assert fits(unit, REAL)
        assert fits(unit, COMPLEX)
        assert not fits(REAL, unit)

    def test_a_narrower_range_fits_a_wider_one(self):
        assert fits(Refine(REAL, ((">=", 1),)), Refine(REAL, ((">=", 0),)))
        assert not fits(Refine(REAL, ((">=", 0),)), Refine(REAL, ((">=", 1),)))
        assert fits(Refine(REAL, ((">", 0),)), Refine(REAL, ((">=", 0),)))
        assert not fits(Refine(REAL, ((">=", 0),)), Refine(REAL, ((">", 0),)))

    def test_fewer_choices_fit_more(self):
        ab = Refine(STRING, (("one-of", ("a", "b")),))
        abc = Refine(STRING, (("one-of", ("a", "b", "c")),))
        assert fits(ab, abc)
        assert not fits(abc, ab)

    def test_const_does_not_change_what_fits(self):
        assert fits(Refine(INT, (("const",),)), INT)
        assert fits(INT, Refine(INT, (("const",),)))

    @pytest.mark.parametrize(
        "text, message",
        [
            ("(real (>= 'a'))", "a comparison takes a number"),
            ("(real (>= 0 1))", "a comparison takes one number"),
            ("(string (>= 0))", "only numbers can be compared"),
            ("(real (length 3))", "only lists have a length"),
            ("(real (one-of 'a'))", "only strings have choices"),
            ("(string (one-of))", "one-of needs at least one choice"),
            ("(real (foo))", "unknown constraint"),
        ],
    )
    def test_invalid(self, text, message):
        with pytest.raises(TypeError_, match=message):
            type_from_node(node(text))


class TestLiteralsAgainstConstraints:
    unit = Refine(REAL, ((">=", 0), ("<=", 1)))

    def test_a_known_value_inside(self):
        assert literal_type(RealLit(0.5), self.unit) == self.unit

    def test_a_known_value_outside_is_an_error(self):
        with pytest.raises(TypeError_, match=r"1.5 breaks \(<= 1\)"):
            literal_type(RealLit(1.5), self.unit)

    def test_strict_bounds(self):
        with pytest.raises(TypeError_, match=r"breaks \(> 0\)"):
            literal_type(IntLit(0), Refine(REAL, ((">", 0),)))

    def test_choices(self):
        side = Refine(STRING, (("one-of", ("left", "right")),))
        assert literal_type(StrLit("left"), side) == side
        with pytest.raises(TypeError_, match="'up' is not one of 'left', 'right'"):
            literal_type(StrLit("up"), side)

    def test_length(self):
        three = Refine(ListT(REAL), (("length", 3),))
        assert literal_type(ListLit((IntLit(1), IntLit(2), IntLit(3))), three) == three
        with pytest.raises(TypeError_, match="2 items, but its length is 3"):
            literal_type(ListLit((IntLit(1), IntLit(2))), three)


class TestNamedTypes:
    def test_a_name_reads_the_types_declared_so_far(self):
        unit = Refine(REAL, ((">=", 0), ("<=", 1)), "unit")
        named = {"unit": unit}
        assert type_from_node(node("unit"), named) == unit
        assert type_from_node(node("list[unit]"), named) == ListT(unit)

    def test_a_named_type_narrows_further(self):
        named = {"unit": Refine(REAL, ((">=", 0), ("<=", 1)), "unit")}
        t = type_from_node(node("(unit (<= 0.5))"), named)
        assert fits(t, named["unit"])
        assert t.base == REAL

    def test_its_name_shows_in_messages(self):
        assert str(Refine(REAL, ((">=", 0),), "positive")) == "positive"
        assert str(Refine(REAL, ((">=", 0),))) == "(real (>= 0))"
