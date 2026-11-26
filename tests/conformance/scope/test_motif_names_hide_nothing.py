"""Conformance tests of the rule motif-names-hide-nothing (docs/spec/scope.md)."""

from ._shared import CompileError, accepted, compile_error, in_folder, pytest, rule, value


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
