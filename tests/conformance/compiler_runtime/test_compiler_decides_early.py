"""Conformance tests of the rule compiler-decides-early (docs/spec/compiler-runtime.md)."""

from ._shared import mtpc, obj, pytest, rule


@rule("compiler-decides-early")
class TestCompilerDecidesEarly:
    @pytest.mark.parametrize(
        "src, v",
        [
            ("(real v (* 2 (+ 1 2)))", 6),
            ("(func f ((real x)) (* 2 x)) (real v (f 3))", 6),
            ("(string v f'{(* 2 3)}')", "6"),
            ("(real v (if (> 2 1) 1 2))", 1),
        ],
    )
    def test_what_is_known_when_compiling_is_computed_then(self, src, v):
        assert obj(mtpc(src), "v")["value"]["free"] == v
