"""Conformance tests of the rule import-declares-names (docs/spec/grammar.md)."""

from ._shared import IMPORT_ORDER, REJECTION, in_folder, pytest, rule


@rule("import-declares-names")
class TestImportDeclaresNames:
    def test_a_name_used_after_the_import(self, tmp_path):
        in_folder(
            tmp_path, {}, "(import colors)\n(scene s (circle c (fill colors.tab10-named.red)))\n"
        )

    @IMPORT_ORDER
    def test_a_name_used_before_the_import_is_an_error(self, tmp_path):
        with pytest.raises(REJECTION):
            in_folder(
                tmp_path,
                {},
                "(scene s (circle c (fill colors.tab10-named.red)))\n(import colors)\n",
            )
