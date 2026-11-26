"""Conformance tests of the rule compiler-reads-files (docs/spec/compiler-runtime.md)."""

from ._shared import REJECTION, in_folder, pytest, rule


@rule("compiler-reads-files")
class TestCompilerReadsFiles:
    def test_an_import_is_looked_for_next_to_the_file_first(self, tmp_path):
        files = {"colors.mtp": "(color mine #'teal')\n"}
        m = in_folder(tmp_path, files, "(import colors)\n(color v colors.mine)\n")
        assert "colors.mine" in m.names

    def test_then_in_the_standard_library(self, tmp_path):
        m = in_folder(tmp_path, {}, "(import colors)\n(color v colors.tab10-named.red)\n")
        assert "v" in m.names

    def test_through_other_imports(self, tmp_path):
        files = {"a.mtp": "(import b)\n(color ink b.pen)\n", "b.mtp": "(color pen #'teal')\n"}
        m = in_folder(tmp_path, files, "(import a)\n(color v a.ink)\n")
        assert "v" in m.names

    def test_an_import_that_is_found_nowhere(self, tmp_path):
        with pytest.raises(REJECTION):
            in_folder(tmp_path, {}, "(import no-such-file)\n")
