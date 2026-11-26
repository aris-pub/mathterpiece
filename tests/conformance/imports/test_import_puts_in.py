"""Conformance tests of the rule import-puts-in (docs/spec/imports.md)."""

from ._shared import IMPORT_DOT, QUALIFIED, REJECTION, in_folder, pytest, rejected_in, rule


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
