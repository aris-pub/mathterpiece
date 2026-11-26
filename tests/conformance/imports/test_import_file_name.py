"""Conformance tests of the rule import-file-name (docs/spec/imports.md)."""

from ._shared import IMPORT_CASE, in_folder, rejected_in, rule


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
