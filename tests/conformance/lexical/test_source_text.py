"""Conformance tests of the rule source-text (docs/spec/lexical.md)."""

from ._shared import StrLit, forms, items, main, rule, syntax_error


@rule("source-text")
class TestSourceText:
    def test_a_file_is_read_with_universal_newlines(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_bytes(b"(string v 'a\r\nb\rc')\r\n")
        main(["compile", str(src)])
        import json

        d = json.loads((tmp_path / "f.mtpc").read_text(encoding="utf-8"))
        assert d["objects"][d["names"]["v"]]["value"]["free"] == "a\nb\nc"

    def test_a_byte_order_mark_at_the_start_is_ignored(self):
        assert forms("﻿(f)") == forms("(f)")

    def test_a_file_that_starts_with_a_byte_order_mark_compiles(self, tmp_path):
        src = tmp_path / "f.mtp"
        src.write_bytes("﻿(real v 1)\n".encode())
        main(["compile", str(src)])
        assert (tmp_path / "f.mtpc").exists()

    def test_a_byte_order_mark_between_forms_is_an_error(self):
        syntax_error("(f)﻿(g)")

    def test_a_byte_order_mark_inside_a_form_is_an_error(self):
        syntax_error("(f ﻿ a)")

    def test_other_text_is_kept_as_written(self):
        assert items("(f 'é ∑ θ')") == (StrLit("é ∑ θ"),)
