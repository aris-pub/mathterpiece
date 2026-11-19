"""Conformance tests for docs/spec/imports.md."""

import pytest

from .support import REJECTION, in_folder

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


IMPORT_DOT = xfail("mtp-ydd4.7.47", "after (import F), (. F N) is an unknown name")


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
            "lib.mtp": "(color ink 'navy')\n",
            "other.mtp": "(import lib)\n(color pen lib.ink)\n",
        }
        m = in_folder(tmp_path, files, "(import lib)\n(import other)\n(color v lib.ink)\n")
        assert [o.name for o in m.objects].count("lib.ink") == 1
