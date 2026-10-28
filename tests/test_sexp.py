from mathterpiece.sexp import next_sexp, toplevel_sexps


def split(src):
    return list(toplevel_sexps(src))


class TestToplevelSexps:
    def test_empty(self):
        assert split("") == []

    def test_only_whitespace(self):
        assert split("   \n\t ") == []

    def test_single_atom(self):
        assert split("circle") == ["circle"]

    def test_atoms(self):
        assert split("a 'b' 3.5") == ["a", "'b'", "3.5"]

    def test_single_list(self):
        assert split("(r 1)") == ["(r 1)"]

    def test_nested_list_stays_whole(self):
        assert split("(x (rand (mult 2 3) 10))") == ["(x (rand (mult 2 3) 10))"]

    def test_mixed_atoms_and_lists(self):
        assert split("a (b (c d)) (e) f") == ["a", "(b (c d))", "(e)", "f"]

    def test_extra_whitespace_between_items(self):
        assert split("  (a)   (b)\n\n(c)  ") == ["(a)", "(b)", "(c)"]

    def test_adjacent_lists(self):
        assert split("(a)(b)") == ["(a)", "(b)"]


class TestNextSexp:
    def test_head_and_rest(self):
        assert next_sexp("circle 'disk' (r 1)") == ("circle", "'disk' (r 1)")

    def test_head_only(self):
        assert next_sexp("circle") == ("circle", "")

    def test_list_head(self):
        assert next_sexp("(r 1) (x 2)") == ("(r 1)", "(x 2)")

    def test_rest_whitespace_is_normalized(self):
        assert next_sexp("a   (b)\n  (c)") == ("a", "(b) (c)")
