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
