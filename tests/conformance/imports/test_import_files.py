"""Conformance tests of the rule import-files (docs/spec/imports.md)."""

from ._shared import in_folder, pytest, rejected_in, rule


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
