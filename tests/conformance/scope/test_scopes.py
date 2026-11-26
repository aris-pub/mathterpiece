"""Conformance tests of the rule scopes (docs/spec/scope.md)."""

from ._shared import accepted, compile_error, pytest, rule, value


@rule("scopes")
class TestScopes:
    @pytest.mark.parametrize(
        "src",
        [
            "(real v (let ((k 2)) k)) (real w k)",
            "(real v (let ((j k) (k 2)) j))",
            "(scene s (foreach i 2 (circle_ (r 1)))) (real v i)",
            "(func f ((real x)) x) (real v x)",
            "(func f ((real a) (real b a)) b)",
            "(motif dot () (circle face (r 1))) (scene s (dot d1)) (real v face.r)",
            "(namespace n (real a 1)) (real v a)",
            "(formula f $'\\term{a}{x}' (term a (fill #'red'))) (color|none v a.fill)",
        ],
    )
    def test_a_name_used_outside_its_scope_is_an_error(self, src):
        compile_error(src)

    def test_a_let_name_may_be_used_by_the_names_after_it(self):
        assert value("(real v (let ((k 2) (j (* k 3))) j))", "v") == 6

    @pytest.mark.parametrize(
        "src",
        [
            "(scene s (group g (circle c (r 1)))) (real v c.r)",
            "(scene s (let ((k 1)) (circle c (r k)))) (real v c.r)",
            "(scene s (foreach k 2 (circle @'c-{k}' (r 1)))) (real v c-1.r)",
        ],
    )
    def test_the_shapes_of_the_scene_are_names_of_the_file_scope(self, src):
        accepted(src)

    def test_a_member_of_a_body_is_used_outside_through_its_declaration(self):
        accepted("(motif dot () (circle face (r 1))) (scene s (dot d1)) (real v d1.face.r)")
        accepted("(namespace n (real a 1) (real b a)) (real v n.b)")
        accepted("(formula f $'\\term{a}{x}' (term a (fill #'red'))) (color|none v f.a.fill)")

    def test_a_let_in_a_motif_body_declares_into_the_body(self):
        src = "(motif m () (let ((k 1)) (circle c (r k)))) (scene s (m d)) (real v d.c.r)"
        assert value(src, "v") == 1

    def test_two_formulas_may_each_have_a_term_of_the_same_name(self):
        accepted(
            "(formula f $'\\term{a}{x}' (term a (fill #'red')))"
            " (formula g $'\\term{a}{y}' (term a (fill #'blue')))"
        )
