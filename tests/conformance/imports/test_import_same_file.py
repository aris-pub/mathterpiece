"""Conformance tests of the rule import-same-file (docs/spec/imports.md)."""

from ._shared import ROOT, in_folder, rejected_in, rule


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
