"""Conformance tests of the rule import-file-holds (docs/spec/imports.md)."""

from ._shared import BOUND_IN_FILE, FREE_COLOR, in_folder, pytest, rejected_in, rule


@rule("import-file-holds")
class TestImportFileHolds:
    def test_the_forms_that_a_file_to_import_may_hold(self, tmp_path):
        lib = {
            "lib.mtp": "(import math dot)\n"
            "(type pos real (>= 0))\n"
            "(interface inky (color ink))\n"
            "(func f ((pos x)) x)\n"
            "(colormap cm {#'red' #'blue'})\n"
            "(motif m () (circle_ (r 1)))\n"
            "(variant sq ((real side 1)) (rect_ (width side) (height side)))\n"
            "(namespace n (real a 1 (const)))\n"
            "(palette pal (ink #'navy'))\n"
            "(font fo (size 12))\n"
            "(rand-seed sd 1)\n"
            "(real k 2 (const))\n"
            "(let ((a 2)) (real j a (const)))\n"
            "(foreach i 2 (real @'k-{i}' i (const)))\n"
        }
        m = in_folder(tmp_path, lib, "(import lib)\n(real v lib.j)\n")
        assert m.get("v").value.value == 2

    @BOUND_IN_FILE
    def test_a_bound_variable(self, tmp_path):
        lib = {"lib.mtp": "(real k 2 (const))\n(real j (* 2 k))\n"}
        in_folder(tmp_path, lib, "(import lib)\n")

    @pytest.mark.parametrize(
        "text",
        [
            "(real k 1)\n",
            "(scene s (circle c (r 1)))\n",
            "(real k 0 (const))\n(slider sl (animation (move k (from 0) (to 1) (duration 0))))\n",
            "(formula fo $'x')\n",
            pytest.param("(color ink #'navy')\n", marks=FREE_COLOR),
        ],
    )
    def test_anything_else_is_a_compile_error(self, tmp_path, text):
        rejected_in(tmp_path, {"lib.mtp": text}, "(import lib)\n")
