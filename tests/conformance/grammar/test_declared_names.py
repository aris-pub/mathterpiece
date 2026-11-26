"""Conformance tests of the rule declared-names (docs/spec/grammar.md)."""

from ._shared import accepted, compile_error, mtpc, obj, pytest, rule


@rule("declared-names")
class TestDeclaredNames:
    def test_a_name_string(self):
        d = mtpc("(scene s (foreach i 2 (circle @'d-{i}' (r 1))))")
        assert {"d-0", "d-1"} <= set(d["names"])

    def test_the_name_form(self):
        d = mtpc("(scene s (circle (name 'c') (r 1)))")
        assert obj(d, "c")["kind"] == "circle"

    def test_none_means_no_name(self):
        d = mtpc("(scene s (circle none (r 1)))")
        assert [o for o in d["objects"] if o["kind"] == "circle"][0].get("name") is None

    def test_a_name_in_quotes_is_an_error(self):
        compile_error("(real 'k' 1)")

    def test_the_string_of_a_name_string_is_known_when_compiling(self):
        compile_error("(real j 1) (scene s (circle @'c-{j}' (r 1)))")

    @pytest.mark.parametrize("src", ["(scene none (circle c (r 1)))", "(scene_ (circle c (r 1)))"])
    def test_a_scene_must_have_a_name(self, src):
        compile_error(src)

    @pytest.mark.parametrize("src", ["(formula none $'x')", "(formula_ $'x')"])
    def test_a_formula_must_have_a_name(self, src):
        compile_error(src)

    def test_a_view_must_have_a_name(self):
        compile_error("(scene s (circle c (r 1))) (canvas none s)")

    def test_a_control_must_have_a_name(self):
        compile_error(
            "(real k 0 (>= 0) (<= 1)) "
            "(slider none (animation (move k (from 0) (to 1) (duration 0))))"
        )

    @pytest.mark.parametrize(
        "src",
        [
            "(func none ((real x)) (* 2 x))",
            "(func_ ((real x)) (* 2 x))",
            "(func[real] none ((real x)) (* 2 x))",
            "(func none ((real x)) x) (func none ((real y)) y)",
        ],
    )
    def test_a_function_may_have_no_name(self, src):
        accepted(src)

    def test_the_body_of_a_function_with_no_name_is_compiled(self):
        compile_error("(func_ ((real x)) (* 2 y))")
        compile_error("(func[(real (>= 0) (<= 1))] none ((real x)) (* 2 x))")

    @pytest.mark.parametrize(
        "src",
        [
            "(motif none ((real k 1 (>= 0))) (circle c (r k)))",
            "(motif_ ((real k 1 (>= 0))) (circle c (r k)))",
            "(motif_ ((real k 1 (>= 0))) (circle c (r k)))"
            " (motif_ ((real m 1 (>= 0))) (circle c (r m)))",
            "(motif_ ((real k 1 (>= 0))) (circle c (r k))) (scene s (circle c (r 1)))",
        ],
    )
    def test_a_motif_may_have_no_name(self, src):
        accepted(src)

    def test_the_body_of_a_motif_with_no_name_is_compiled(self):
        compile_error("(motif_ ((real k 1 (>= 0))) (circle c (r m)))")
