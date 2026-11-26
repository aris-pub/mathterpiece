"""Conformance tests of the rule import-checks-whole-file (docs/spec/imports.md)."""

from ._shared import pytest, rejected_in, rule


@rule("import-checks-whole-file")
class TestImportChecksWholeFile:
    @pytest.mark.parametrize(
        "text", ["(func broken ((real x)) (+ x 'a'))\n", "(real k (/ 1 0) (const))\n"]
    )
    def test_an_error_in_a_declaration_that_the_source_does_not_use(self, tmp_path, text):
        lib = {"lib.mtp": "(func twice ((real x)) (* 2 x))\n" + text}
        rejected_in(tmp_path, lib, "(import lib twice)\n(real v (twice 2))\n")
