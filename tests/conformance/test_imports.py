"""Conformance tests for docs/spec/imports.md.

The rule import-declares-names has its tests in test_grammar.py."""

import tempfile
from pathlib import Path

import pytest

from mathterpiece.compiler import CompileError

from .support import REJECTION, ROOT, accepted, compile_error, in_folder

rule = pytest.mark.rule


def xfail(bead: str | None, why: str, condition: bool = True):
    reason = f"{bead}: {why}" if bead else why
    return pytest.mark.xfail(condition, strict=True, reason=reason)


def _case_blind() -> bool:
    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / "probe.mtp").write_text("", encoding="utf-8")
        return (Path(folder) / "PROBE.mtp").exists()


IMPORT_DOT = xfail("mtp-ydd4.7.47", "after (import F), (. F N) is an unknown name")
IMPORT_CASE = xfail(
    "mtp-ydd4.7.57",
    "on a file system that does not tell upper and lower case apart, the import finds the file",
    _case_blind(),
)
QUALIFIED = xfail(None, "after (import F N), F.N is an unknown name")
BOUND_IN_FILE = xfail(None, "a file to import may not hold a bound variable")
FREE_COLOR = xfail(None, "a file to import may hold a free color variable")


def rejected_in(folder: Path, files: dict[str, str], main: str) -> None:
    """Writes the files into the folder, and a later step than the parse step rejects main."""
    with pytest.raises(CompileError):
        in_folder(folder, files, main)


@rule("import-form")
class TestImportForm:
    def test_the_two_ways_of_writing_an_import(self, tmp_path):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n(func thrice ((real x)) (* 3 x))\n"}
        in_folder(tmp_path, lib, "(import lib)\n")
        assert (
            in_folder(tmp_path, lib, "(import lib twice thrice)\n(real v (thrice 2))\n")
            .get("v")
            .value.value
            == 6
        )

    def test_a_file_of_the_standard_library(self):
        assert accepted("(import math dot clamp) (real v (clamp 5 0 1))").get("v").value.value == 1

    @pytest.mark.parametrize(
        "src",
        ["(import)", "(import 'colors')", "(import colors.okabe-ito)", "(import math (dot))"],
    )
    def test_any_other_import_is_a_compile_error(self, src):
        compile_error(src)

    def test_a_name_that_the_file_does_not_have(self, tmp_path):
        rejected_in(tmp_path, {"lib.mtp": "(real k 3 (const))\n"}, "(import lib j)\n")


@rule("import-file-name")
class TestImportFileName:
    @IMPORT_CASE
    def test_the_name_matches_case_included(self, tmp_path):
        rejected_in(tmp_path, {"lib.mtp": "(real k 3 (const))\n"}, "(import Lib)\n")

    def test_no_folder_holds_the_file(self, tmp_path):
        rejected_in(tmp_path, {}, "(import nosuchfile)\n")

    def test_a_file_next_to_the_source_comes_before_the_standard_library(self, tmp_path):
        colors = {"colors.mtp": "(real k 3 (const))\n"}
        m = in_folder(tmp_path, colors, "(import colors)\n(real v colors.k)\n")
        assert m.get("v").value.value == 3


@rule("import-same-file")
class TestImportSameFile:
    def test_a_file_imported_twice_is_put_in_once(self, tmp_path):
        files = {
            "lib.mtp": "(real k 3 (const))\n",
            "other.mtp": "(import lib)\n(real j lib.k (const))\n",
        }
        m = in_folder(tmp_path, files, "(import lib)\n(import other)\n(real v lib.k)\n")
        assert [o.name for o in m.objects].count("lib.k") == 1

    def test_a_symbolic_link_to_the_same_file(self, tmp_path):
        # The file ease of the standard library imports the file types of the standard library.
        (tmp_path / "types.mtp").symlink_to(ROOT / "mathterpiece" / "stdlib" / "types.mtp")
        in_folder(tmp_path, {}, "(import types)\n(import ease)\n")

    def test_two_different_files_of_the_same_name(self, tmp_path):
        rejected_in(
            tmp_path, {"types.mtp": "(real k 3 (const))\n"}, "(import types)\n(import ease)\n"
        )

    def test_a_file_that_imports_itself(self, tmp_path):
        rejected_in(tmp_path, {"lib.mtp": "(import lib)\n(real k 3 (const))\n"}, "(import lib)\n")

    def test_a_file_that_imports_itself_through_another(self, tmp_path):
        files = {"a.mtp": "(import b)\n(real k 3 (const))\n", "b.mtp": "(import a)\n"}
        rejected_in(tmp_path, files, "(import a)\n")


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


@rule("import-checks-whole-file")
class TestImportChecksWholeFile:
    @pytest.mark.parametrize(
        "text", ["(func broken ((real x)) (+ x 'a'))\n", "(real k (/ 1 0) (const))\n"]
    )
    def test_an_error_in_a_declaration_that_the_source_does_not_use(self, tmp_path, text):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n" + text}
        rejected_in(tmp_path, lib, "(import lib twice)\n(real v (twice 2))\n")


@rule("import-puts-in")
class TestImportPutsIn:
    def test_import(self, tmp_path):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n"}
        a = in_folder(tmp_path, lib, "(import lib)\n(real v (lib.twice 2))\n")
        assert a.get("v").value.value == 4

    @IMPORT_DOT
    def test_import_and_the_dot_form(self, tmp_path):
        lib = {"lib.mtp": "(real k 3 (const))\n"}
        m = in_folder(tmp_path, lib, "(import lib)\n(real v (. lib k))\n")
        assert m.get("v").value.value == 3

    def test_import_of_names(self, tmp_path):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n"}
        m = in_folder(tmp_path, lib, "(import lib twice)\n(real v (twice 2))\n")
        assert m.get("v").value.value == 4

    @QUALIFIED
    def test_import_of_names_also_gives_the_qualified_names(self, tmp_path):
        lib = {"lib.mtp": "(real k 3 (const))\n"}
        m = in_folder(tmp_path, lib, "(import lib k)\n(real v k)\n(real w lib.k)\n")
        assert m.get("w").value.value == 3

    def test_import_of_a_whole_file_gives_no_name_on_its_own(self, tmp_path):
        rejected_in(tmp_path, {"lib.mtp": "(real k 3 (const))\n"}, "(import lib)\n(real v k)\n")

    def test_import_of_a_name_that_the_file_does_not_declare(self, tmp_path):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n"}
        with pytest.raises(REJECTION):
            in_folder(tmp_path, lib, "(import lib thrice)\n")

    def test_import_of_a_name_that_the_source_declares(self, tmp_path):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n"}
        with pytest.raises(REJECTION):
            in_folder(tmp_path, lib, "(import lib twice)\n(func twice ((real x)) x)\n")

    def test_a_file_imported_twice_is_put_in_once(self, tmp_path):
        files = {
            "lib.mtp": "(color ink #'navy' (const))\n",
            "other.mtp": "(import lib)\n(color pen lib.ink (const))\n",
        }
        m = in_folder(tmp_path, files, "(import lib)\n(import other)\n(color v lib.ink)\n")
        assert [o.name for o in m.objects].count("lib.ink") == 1


@rule("import-files")
class TestImportFiles:
    def test_an_imported_file_may_not_use_a_name_of_the_source(self, tmp_path):
        lib = {"lib.mtp": "(real j k (const))\n"}
        rejected_in(tmp_path, lib, "(real k 3 (const))\n(import lib)\n")

    def test_a_name_imported_by_name_is_a_name_of_the_file(self, tmp_path):
        files = {"base.mtp": "(real red 3 (const))\n", "house.mtp": "(import base red)\n"}
        assert (
            in_folder(tmp_path, files, "(import house red)\n(real v red)\n").get("v").value.value
            == 3
        )
        assert (
            in_folder(tmp_path, files, "(import house)\n(real v house.red)\n").get("v").value.value
            == 3
        )

    @pytest.mark.parametrize(
        "main", ["(import house base)\n", "(import house)\n(real v house.base.red)\n"]
    )
    def test_the_name_of_a_file_imported_whole_is_not_a_name_of_the_file(self, tmp_path, main):
        files = {"base.mtp": "(real red 3 (const))\n", "house.mtp": "(import base)\n"}
        rejected_in(tmp_path, files, main)
