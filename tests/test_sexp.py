import pytest

from mathterpiece.main import Parser


@pytest.fixture
def prs():
    return Parser("")


def split(prs, src):
    return list(prs.toplevel_sexps(src))


class TestToplevelSexps:
    def test_empty(self, prs):
        assert split(prs, "") == []

    def test_only_whitespace(self, prs):
        assert split(prs, "   \n\t ") == []

    def test_single_atom(self, prs):
        assert split(prs, "circle") == ["circle"]

    def test_atoms(self, prs):
        assert split(prs, "a 'b' 3.5") == ["a", "'b'", "3.5"]

    def test_single_list(self, prs):
        assert split(prs, "(r 1)") == ["(r 1)"]

    def test_nested_list_stays_whole(self, prs):
        assert split(prs, "(x (rand (mult 2 3) 10))") == ["(x (rand (mult 2 3) 10))"]

    def test_mixed_atoms_and_lists(self, prs):
        assert split(prs, "a (b (c d)) (e) f") == ["a", "(b (c d))", "(e)", "f"]

    def test_extra_whitespace_between_items(self, prs):
        assert split(prs, "  (a)   (b)\n\n(c)  ") == ["(a)", "(b)", "(c)"]

    def test_adjacent_lists(self, prs):
        assert split(prs, "(a)(b)") == ["(a)", "(b)"]


class TestNextSexp:
    def test_head_and_rest(self, prs):
        assert prs.next_sexp("circle 'disk' (r 1)") == ("circle", "'disk' (r 1)")

    def test_head_only(self, prs):
        assert prs.next_sexp("circle") == ("circle", "")

    def test_list_head(self, prs):
        assert prs.next_sexp("(r 1) (x 2)") == ("(r 1)", "(x 2)")

    def test_rest_whitespace_is_normalized(self, prs):
        assert prs.next_sexp("a   (b)\n  (c)") == ("a", "(b) (c)")
