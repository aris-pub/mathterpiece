"""Conformance tests for docs/spec/scope.md.

The rule declaration-names has its tests in test_lexical.py, and declare-before-use has more tests
in test_overview.py."""

import pytest

from mathterpiece.compiler import CompileError

from .support import accepted, compile_error, in_folder, mtpc, obj, value

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


AS_NAME = xfail("mtp-t8in", "the compiler has no (as N), and binds self and pointer itself")
LET_TWICE = xfail("mtp-ydd4.7.41", "the names of one let may be the same")

DRAG = "(real a 1 (>= 0) (<= 4)) (scene s (circle p (pos [a 0]) (r 0.2))) "
DOT = "(scene s (dot d))"


@rule("declarations-and-bindings")
class TestDeclarationsAndBindings:
    def test_a_declaration_with_no_name_creates_an_object(self):
        assert len(obj(mtpc("(scene s (circle_ (r 1)))"), "s")["members"]) == 1

    def test_a_listener_with_no_name_is_created(self):
        d = mtpc(
            "(real k 0) (scene s (circle p (r 1)))"
            " (canvas cv s (on-click p (move k (to 1) (duration 1))))"
        )
        assert [o["kind"] for o in d["objects"]].count("on-click") == 1

    def test_a_binding_creates_nothing(self):
        bound = mtpc("(real v (let ((k 2)) k))")
        plain = mtpc("(real v 2)")
        assert "k" not in bound["names"]
        assert len(bound["objects"]) == len(plain["objects"])

    @AS_NAME
    def test_as_names_the_shape_being_declared_in_a_motif(self):
        accepted("(motif dot () (as me) (circle c (r 1)) (text_ (or? me.name 'a'))) " + DOT)

    @AS_NAME
    def test_as_names_the_position_of_the_pointer(self):
        accepted(DRAG + "(canvas cv s (on-drag p (as ptr) (move a (to ptr.x))))")

    @AS_NAME
    def test_the_language_binds_no_self(self):
        compile_error("(motif dot () (circle c (r 1)) (text_ (or? self.name 'a'))) " + DOT)

    @AS_NAME
    def test_the_language_binds_no_pointer(self):
        compile_error(DRAG + "(canvas cv s (on-drag p (move a (to pointer.x))))")


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


@rule("declare-before-use")
class TestDeclareBeforeUse:
    def test_a_canvas_comes_after_the_scene_in_its_body(self):
        compile_error("(canvas cv s) (scene s (circle c (r 1)))")
        accepted("(scene s (circle c (r 1))) (canvas cv s)")

    def test_an_exists_when_comes_after_its_shape(self):
        compile_error("(scene s (exists-when c true) (circle|none c (r 1)))")
        accepted("(scene s (circle|none c (r 1)) (exists-when c true))")


@rule("name-lookup")
class TestNameLookup:
    def test_a_parameter_hides_a_variable(self):
        src = "(real x 1 (>= 0) (<= 4)) (func tenfold ((real x)) (* 10 x)) (real v (tenfold 2))"
        assert value(src, "v") == 20

    def test_a_let_name_hides_a_name_of_the_file_scope(self):
        assert value("(real k 5 (const)) (real v (let ((k 2)) k))", "v") == 2

    def test_a_foreach_name_hides_a_name_of_the_file_scope(self):
        src = "(real i 5 (const)) (scene s (foreach i 2 (circle @'c-{i}' (r (+ i 1)))))"
        assert value(src + " (real v c-1.r)", "v") == 2

    def test_an_attribute_of_a_record_hides_a_top_level_name_inside_the_record(self):
        src = "(real w 5 (const)) (namespace n (real w 1 (const)) (real u w)) (real v n.u)"
        assert value(src, "v") == 1

    def test_a_built_in_is_found_when_no_scope_has_the_name(self):
        assert value("(real v (max 1 2))", "v") == 2

    def test_a_declaration_hides_a_built_in_from_there_on(self):
        src = "(real u (max 1 2)) (func max ((real a) (real b)) a) (real v (max 1 2))"
        assert value(src, "u") == 2
        assert value(src, "v") == 1
        assert value("(real pi 3 (const)) (real v (* 2 pi))", "v") == 6

    def test_the_parts_after_the_first_are_not_looked_up(self):
        m = accepted("(real r 5 (const)) (scene s (circle p (r 1))) (real v p.r)")
        assert (m.id("p"), "r") in m.get("v").value.deps

    @pytest.mark.parametrize(
        "src", ["(real v zz)", "(int v (rand-int 1 6))", "(int v (rand.rand-int 1 6))"]
    )
    def test_a_name_that_is_not_found_is_an_error(self, src):
        compile_error(src)


@rule("one-declaration-per-scope")
class TestOneDeclarationPerScope:
    @pytest.mark.parametrize(
        "src",
        [
            "(real a 1) (real a 2)",
            "(real f 1) (func f ((real x)) x)",
            "(type pos real (>= 0)) (real pos 1)",
            "(func f ((real x)) x) (scene s (circle f (r 1)))",
            "(scene s (group g (circle c (r 1))) (group h (circle c (r 1))))",
            "(func f ((real x) (real x)) x)",
            "(motif m () (circle c (r 1)) (circle c (r 2)))",
            "(motif m ((real c 1)) (circle c (r 1)))",
            "(import math dot dot)",
            pytest.param("(real v (let ((a 1) (a 2)) a))", marks=LET_TWICE),
        ],
    )
    def test_a_second_declaration_of_a_name_is_an_error(self, src):
        compile_error(src)

    def test_the_copies_of_a_foreach_declare_different_names(self):
        accepted("(scene s (foreach k 2 (circle @'dot-{k}' (r 1))))")


@rule("motif-names-hide-nothing")
class TestMotifNamesHideNothing:
    @pytest.mark.parametrize(
        "src",
        [
            "(real c 1) (motif m () (circle c (r 1)))",
            "(real k 1) (motif m () (real k 2) (circle c (r k)))",
        ],
    )
    def test_a_member_named_like_a_top_level_name_is_an_error(self, src):
        compile_error(src)

    def test_a_member_named_like_a_name_imported_by_name_is_an_error(self, tmp_path):
        lib = {"lib.mtp": "(real ink 3 (const))\n"}
        with pytest.raises(CompileError):
            in_folder(tmp_path, lib, "(import lib ink)\n(motif m () (circle ink (r 1)))\n")

    def test_a_motif_in_an_imported_file(self, tmp_path):
        lib = {"lib.mtp": "(real ink 3 (const))\n(motif m () (circle ink (r 1)))\n"}
        with pytest.raises(CompileError):
            in_folder(tmp_path, lib, "(import lib)\n")

    def test_a_file_imported_whole_gives_only_its_own_name(self, tmp_path):
        lib = {"lib.mtp": "(real ink 3 (const))\n"}
        in_folder(tmp_path, lib, "(import lib)\n(motif m () (circle ink (r 1)))\n")

    def test_two_motifs_and_the_scene_may_each_have_a_member_c(self):
        accepted(
            "(motif m () (circle c (r 1))) (motif n () (circle c (r 2)))"
            " (scene s (circle c (r 1)) (m a) (n b))"
        )

    def test_a_let_name_in_the_body_hides_a_top_level_name(self):
        src = "(real k 3 (const)) (motif m () (let ((k 1)) (circle c (r k)))) (scene s (m d))"
        assert value(src + " (real v d.c.r)", "v") == 1
