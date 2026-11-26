"""Conformance tests of the rule import-form (docs/spec/imports.md)."""

from ._shared import accepted, compile_error, in_folder, pytest, rejected_in, rule


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
