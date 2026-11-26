"""Conformance tests of the rule body-let-foreach (docs/spec/grammar.md)."""

from ._shared import (
    ARGUMENT_LET,
    BODY_LET,
    GROUP_EXISTS_WHEN,
    REJECTION,
    accepted,
    compile_error,
    in_folder,
    mtpc,
    pytest,
    rejected,
    rule,
    value,
)


@rule("body-let-foreach")
class TestBodyLetForeach:
    def test_a_foreach_at_the_top_level(self):
        d = mtpc("(foreach i 3 (real @'k-{i}' i))")
        assert {"k-0", "k-1", "k-2"} <= set(d["names"])

    def test_a_let_at_the_top_level(self):
        accepted("(let ((k 2)) (real a k))")

    def test_a_let_at_the_top_level_holds_a_scene(self):
        accepted("(let ((k 2)) (scene s (circle c (r k))))")

    def test_a_scene_in_a_let_reads_its_names(self):
        m = accepted("(let ((k 2)) (scene s (background #'white') (circle c (r k))))")
        assert m.get("c").attrs["r"].value == 2

    def test_a_scene_in_a_foreach_reads_its_names(self):
        m = accepted("(foreach i {2} (scene @'s{i}' (circle c (r i))))")
        assert m.get("c").attrs["r"].value == 2
        assert "s2" in m.names

    def test_a_motif_in_a_let_keeps_its_values_where_it_is_used(self):
        m = accepted(
            "(let ((k 2)) (motif m ((real w k)) (circle c (r (+ k w)))))"
            " (real k 5 (const)) (scene s (m a))"
        )
        assert m.get("a.c").attrs["r"].value == 4

    def test_a_motif_in_a_foreach_reads_its_names(self):
        m = accepted(
            "(foreach i 2 (motif @'m{i}' () (circle c (r (+ i 1))))) (scene s (m1 a) (m0 b))"
        )
        assert m.get("a.c").attrs["r"].value == 2
        assert m.get("b.c").attrs["r"].value == 1

    def test_a_function_in_a_let_keeps_its_values_where_it_is_called(self):
        src = "(let ((k 2)) (func f ((real x)) (* k x))) (real k 5 (const)) (real v (f 1))"
        assert value(src, "v") == 2

    def test_a_function_in_a_let_called_on_a_free_variable(self):
        m = accepted(
            "(let ((k 2)) (func f ((real x k)) (* k x)))"
            " (real x 1 (>= 0) (<= 3)) (real v (f x)) (real w (f))"
        )
        assert m.get("v").value.expr.range == (0, 6)
        assert m.get("w").value.value == 4

    def test_a_function_in_a_foreach_reads_its_names(self):
        assert value("(foreach i 3 (func @'f{i}' ((real x)) (* i x))) (real v (f2 3))", "v") == 6

    def test_an_animation_in_a_let_reads_its_names(self):
        m = accepted("(real a 0) (let ((k 2)) (animation an (move a (to k) (duration k))))")
        assert m.get("an").attrs["duration"].value == 2

    def test_an_animation_in_a_foreach_reads_its_names(self):
        m = accepted(
            "(real a 0) (foreach i {1 2} (animation @'an{i}' (move a (to i) (duration i))))"
        )
        assert m.get("an2").attrs["duration"].value == 2

    def test_a_transition_in_a_let_reads_its_names(self):
        accepted("(real a 0) (let ((k 2)) (transition t a (to k) (duration k)))")

    def test_a_transition_in_a_foreach_reads_its_names(self):
        d = mtpc("(real a 0) (foreach i 2 (transition @'t{i}' a (to i) (duration 1)))")
        assert {"t0", "t1"} <= set(d["names"])

    def test_a_choreo_in_a_let_keeps_its_values_where_it_is_used(self):
        m = accepted(
            "(real a 0) (let ((k 2)) (choreo go ((real d k)) (move a (to k) (duration d))))"
            " (real k 5 (const)) (animation an (go))"
        )
        assert m.get("an").attrs["duration"].value == 2

    def test_a_choreo_in_a_foreach_reads_its_names(self):
        m = accepted(
            "(real a 0) (foreach i {1 2} (choreo @'go{i}' () (move a (to i) (duration i))))"
            " (animation an (go2))"
        )
        assert m.get("an").attrs["duration"].value == 2

    def test_a_type_in_a_foreach_reads_its_names(self):
        accepted("(foreach i 2 (type @'t{i}' real (>= 0))) (t1 v 1)")

    def test_an_interface_in_a_foreach_reads_its_names(self):
        accepted("(foreach i 2 (interface @'has-r{i}' (real r))) (func f ((has-r1 s)) s.r)")

    def test_a_variant_in_a_let_keeps_its_values_where_it_is_used(self):
        m = accepted(
            "(let ((k 2)) (variant big ((real w k)) (circle_ (r (+ k w)))))"
            " (real k 5 (const)) (scene s (big b))"
        )
        assert m.get("b").attrs["r"].value == 4

    def test_a_variant_in_a_foreach_reads_its_names(self):
        m = accepted("(foreach i 2 (variant @'v{i}' () (circle_ (r (+ i 1))))) (scene s (v1 b))")
        assert m.get("b").attrs["r"].value == 2

    def test_a_colormap_in_a_let_reads_its_names(self):
        m = accepted(
            "(let ((c #'red') (k 2)) (colormap cm {c #'blue'} (positions {0 k})))"
            " (color v (cm 0)) (color w (cm 2))"
        )
        assert m.get("v").value.value != m.get("w").value.value

    def test_a_colormap_in_a_foreach_reads_its_names(self):
        accepted("(foreach i 2 (colormap @'cm{i}' {#'red' #'blue'} (positions {0 (+ i 1)})))")

    def test_a_let_in_a_foreach_at_the_top_level(self):
        d = mtpc("(foreach i 3 (let ((k (* 2 i))) (real @'v-{i}' k)))")
        assert {"v-0", "v-1", "v-2"} <= set(d["names"])

    def test_a_let_at_the_top_level_of_a_file_to_import(self, tmp_path):
        lib = {"lib.mtp": "(let ((k 2)) (real v k (const)))\n"}
        in_folder(tmp_path, lib, "(import lib)\n(real w lib.v)\n")

    def test_a_foreach_at_the_top_level_of_a_file_to_import(self, tmp_path):
        lib = {"lib.mtp": "(foreach i 3 (real @'v{i}' i (const)))\n"}
        in_folder(tmp_path, lib, "(import lib)\n(real w lib.v2)\n")

    def test_a_let_in_a_foreach_in_a_file_to_import(self, tmp_path):
        lib = {"lib.mtp": "(foreach i 3 (let ((k (* 2 i))) (real @'v{i}' k (const))))\n"}
        in_folder(tmp_path, lib, "(import lib)\n(real w lib.v2)\n")

    @pytest.mark.parametrize(
        "text",
        [
            "(let ((k 2)) (real v k))",
            "(foreach i 3 (real @'v{i}' i))",
            "(foreach i 3 (let ((k i)) (real @'v{i}' k)))",
        ],
    )
    def test_a_file_to_import_holds_in_a_let_or_foreach_only_what_it_may(self, tmp_path, text):
        with pytest.raises(REJECTION):
            in_folder(tmp_path, {"lib.mtp": text + "\n"}, "(import lib)\n")

    def test_a_file_to_import_holds_no_scene_in_a_let(self, tmp_path):
        lib = {"lib.mtp": "(let ((k 2)) (scene s (circle c (r 1))))\n"}
        with pytest.raises(REJECTION):
            in_folder(tmp_path, lib, "(import lib)\n")

    def test_a_let_in_the_scene(self):
        accepted("(scene s (let ((k 2)) (circle c (r k))))")

    @BODY_LET
    def test_a_let_in_an_animation(self):
        accepted("(real k 0) (animation a (let ((t 1)) (move k (to 1) (duration t))))")

    @BODY_LET
    def test_a_let_in_a_namespace(self):
        accepted("(namespace n (let ((t 1)) (real k t)))")

    @pytest.mark.parametrize(
        "src",
        [
            pytest.param("(scene s (circle c (let ((k 2)) (r k))))", marks=ARGUMENT_LET),
            pytest.param("(scene s (circle c (foreach i 1 (r 2))))", marks=ARGUMENT_LET),
        ],
    )
    def test_never_among_the_arguments_of_a_form(self, src):
        compile_error(src)

    def test_never_in_the_body_of_a_function(self):
        rejected("(func f ((real x)) (let ((k 2)) (real a k)))")

    @GROUP_EXISTS_WHEN
    def test_an_exists_when_names_a_shape_declared_before_it(self):
        compile_error("(scene s (group g (exists-when c true) (circle|none c (r 1))))")
