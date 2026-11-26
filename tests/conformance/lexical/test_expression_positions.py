"""Conformance tests of the rule expression-positions (docs/spec/lexical.md)."""

from ._shared import forms, rule


@rule("expression-positions")
class TestExpressionPositions:
    def test_line_and_column_count_from_1(self):
        (f,) = forms("(f\n  (g)\tx)")
        assert (f.pos.line, f.pos.col) == (1, 1)
        g, x = f.items[1:]
        assert (g.pos.line, g.pos.col) == (2, 3)
        # A tab adds 1 to the column, like every character but a line feed.
        assert (x.pos.line, x.pos.col) == (2, 7)

    def test_a_byte_order_mark_at_the_start_is_not_counted(self):
        (f,) = forms("﻿(f)")
        assert (f.pos.line, f.pos.col) == (1, 1)
