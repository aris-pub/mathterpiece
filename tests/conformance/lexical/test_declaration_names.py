"""Conformance tests of the rule declaration-names (docs/spec/lexical.md)."""

from ._shared import KEYWORD_NAMES, accepted, compile_error, pytest, rule


@rule("declaration-names")
class TestDeclarationNames:
    @pytest.mark.parametrize(
        "src",
        [
            pytest.param("(real if 1)", marks=KEYWORD_NAMES),
            pytest.param("(scene s (circle line (r 1)))", marks=KEYWORD_NAMES),
            "(func if ((real a)) a)",
            pytest.param("(func f ((real if)) if)", marks=KEYWORD_NAMES),
            pytest.param("(real v (let ((if 2)) if))", marks=KEYWORD_NAMES),
            pytest.param("(scene s (foreach if 2 (circle_ (r 1))))", marks=KEYWORD_NAMES),
            pytest.param("(namespace n (real if 1))", marks=KEYWORD_NAMES),
            pytest.param("(palette p (if #'red'))", marks=KEYWORD_NAMES),
            pytest.param("(formula if $'x')", marks=KEYWORD_NAMES),
            pytest.param("(motif if () (circle_ (r 1)))", marks=KEYWORD_NAMES),
            pytest.param("(font if (size 12))", marks=KEYWORD_NAMES),
        ],
    )
    def test_no_declaration_of_any_kind_takes_a_keyword(self, src):
        compile_error(src)

    @pytest.mark.parametrize(
        "word",
        [
            pytest.param(t, marks=KEYWORD_NAMES)
            for t in [
                "int", "ratio", "real", "complex", "bool", "string", "color", "font", "point",
                "transform", "func", "list", "shape", "positioned",
                "sequence",
            ]
        ],
    )  # fmt: skip
    def test_no_declaration_takes_a_built_in_type(self, word):
        compile_error(f"(real {word} 1)")

    def test_no_declaration_takes_the_type_of_seeds(self):
        compile_error("(real rand-seed 1)")

    @pytest.mark.parametrize("word", [pytest.param("pointer", marks=KEYWORD_NAMES), "self"])
    def test_no_declaration_takes_pointer_or_self(self, word):
        compile_error(f"(real {word} 1)")

    @KEYWORD_NAMES
    def test_self_in_a_let(self):
        compile_error("(real v (let ((self 2)) self))")

    def test_a_declaration_may_take_the_name_of_a_built_in_function(self):
        m = accepted("(func max ((real a) (real b)) a) (real v (max 1 2))")
        assert m.get("v").value.value == 1

    @pytest.mark.xfail(
        strict=True, reason="mtp-9rj1: a declaration may take the name of an operator"
    )
    def test_no_declaration_takes_the_name_of_an_operator(self):
        compile_error("(func + ((real a) (real b)) 7)")

    @pytest.mark.parametrize("constant", ["pi", "tau", "euler"])
    def test_a_declaration_may_take_the_name_of_a_built_in_constant(self, constant):
        m = accepted(f"(real {constant} 3) (real v {constant})")
        assert m.get("v").value.deps == {(m.id(constant), None)}

    @KEYWORD_NAMES
    def test_a_function_may_take_the_name_of_a_constant(self):
        m = accepted("(func pi ((real a)) a) (real v (pi 2))")
        assert m.get("v").value.value == 2
