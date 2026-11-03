"""The form template: a head, a name, positional arguments, optional arguments in any order,
then a body (docs/syntax.md, section 8)."""

import pytest

from mathterpiece.compiler import CompileError, compile_source

K = "(real k 0 (>= 0) (<= 10))"


@pytest.mark.parametrize(
    "src",
    [
        "(scene s (circle c) (background 'red'))",
        "(scene s (group g (circle c) (fill 'red')))",
        "(scene s (circle c)) (canvas v c (view-x 1))",
        f"{K} (button b (animation (move k (to 1) (duration 1))) (> k 1) (label 'go'))",
        f"{K} (animation a (move k (to 1) (duration 1)) (defaults (duration 2)))",
    ],
)
def test_an_optional_argument_comes_before_the_body(src):
    with pytest.raises(CompileError, match="comes before"):
        compile_source(src)


@pytest.mark.parametrize(
    "src",
    [
        "(scene s (background 'red') (circle c))",
        "(scene s (group g (translate [1 0]) (defaults (fill 'red') (stroke 'blue')) (circle c)))",
        "(scene s (circle c)) (canvas v (view-x 1) (move none (duration 1)) c)",
        f"{K} (button b (label 'go') (animation (move k (to 1) (duration 1))) (> k 1))",
        f"{K} (animation a (defaults (duration 2)) (move k (to 1)))",
    ],
)
def test_optional_arguments_in_any_order_then_the_body(src):
    compile_source(src)
