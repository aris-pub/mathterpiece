import pytest

from mathterpiece.compiler import CompileError, _Compiler
from mathterpiece.parse import parse
from mathterpiece.transitions import Sequence, Single, Wait


def consts(src):
    compiler = _Compiler(parse(f"{src} (scene _)"))
    compiler.compile()
    return {name: value.value for name, value in compiler.consts.items()}


def const(src):
    (value,) = consts(src).values()
    return value


def error(src, match):
    with pytest.raises(CompileError, match=match):
        consts(src)


class TestSingle:
    def test_parts(self):
        t = const("(const 't' (transition (from 0) (to 3) (duration 2) (ease 'ease-in')))")
        assert t == Single(frm=0.0, to=3.0, duration=2.0, ease="ease-in", path=None, elem="real")

    def test_anything_may_be_left_out(self):
        assert const("(const 't' (transition (duration 1)))") == Single(duration=1.0)
        assert const("(const 't' (transition))") == Single()

    @pytest.mark.parametrize(
        "end, elem",
        [("3", "real"), ("[1 2]", "list2"), ("'red'", "str"), ("true", "bool"), ("2/3", "real")],
    )
    def test_the_type_comes_from_the_ends(self, end, elem):
        assert const(f"(const 't' (transition (to {end})))").elem == elem

    def test_step_ease(self):
        assert const("(const 't' (transition (to true) (ease (step 0.3))))").ease == ("step", 0.3)

    def test_functions_by_name(self):
        src = (
            "(func 'snap' (params (t 0.0)) (* t t))"
            " (func 'arc' (params (a [0.0 0.0]) (b [0.0 0.0]) (t 0.0)) (lerp a b t))"
            " (const 't' (transition (to [1 0]) (ease snap) (path arc)))"
        )
        t = consts(src)["t"]
        assert (t.ease, t.path) == (("func", "snap"), ("func", "arc"))

    def test_a_library_function_as_a_path(self):
        assert const("(const 't' (transition (to 1) (path lerp)))").path == ("func", "lerp")


class TestComposed:
    def test_in_order(self):
        t = const(
            "(const 't' (in-order (default-duration 1) (default-ease 'ease-in-out')"
            " (ease 'ease-in') (transition (to 90)) (wait 0.5) (transition (to 180) (duration 2))))"
        )
        assert t == Sequence(
            parts=(
                Single(to=90.0, elem="real"),
                Wait(0.5),
                Single(to=180.0, duration=2.0, elem="real"),
            ),
            ease="ease-in",
            default_duration=1.0,
            default_ease="ease-in-out",
            elem="real",
        )

    def test_nested(self):
        t = consts("(const 'a' (transition (to 1))) (const 'b' (in-order a (in-order a a)))")["b"]
        assert t.parts[1].parts == (Single(to=1.0, elem="real"), Single(to=1.0, elem="real"))

    def test_a_wait_alone(self):
        assert const("(const 'w' (wait 2))") == Wait(2.0)


class TestErrors:
    @pytest.mark.parametrize(
        "src, match",
        [
            ("(const 't' (transition (from 0) (to 'red')))", "from is a real but to is a str"),
            ("(const 't' (transition (duration -1)))", "a duration cannot be negative"),
            ("(const 't' (transition (ease 'wobbly')))", "ease is one of"),
            ("(const 't' (transition (ease (step 2))))", "step takes a number from 0 to 1"),
            ("(const 't' (transition (path nope)))", "no function named 'nope'"),
            (
                "(func 'snap' (params (t 0.0)) t) (const 't' (transition (path snap)))",
                "a path takes three parameters",
            ),
            (
                "(func 'two' (params (a 0.0) (b 0.0)) a) (const 't' (transition (ease two)))",
                "an ease takes one parameter",
            ),
            ("(const 't' (transition (speed 2)))", "transition has no part 'speed'"),
            ("(const 't' (transition (to 1) (to 2)))", "'to' is given twice"),
            ("(const 't' (in-order 3))", "in-order holds transitions"),
            (
                "(const 't' (in-order (transition (to 1)) (transition (to 'a'))))",
                "the steps of an in-order move different types",
            ),
            ("(const 'w' (wait))", "wait takes a number of seconds"),
            (
                "(real 'k') (const 't' (transition (to k)))",
                "a const transition cannot read the scene",
            ),
        ],
    )
    def test_invalid(self, src, match):
        error(src, match)
