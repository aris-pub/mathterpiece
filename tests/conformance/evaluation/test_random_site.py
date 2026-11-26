"""Conformance tests of the rule random-site (docs/spec/evaluation.md)."""

from ._shared import RAND, SITES, _sites, mtpc, obj, rule


@rule("random-site")
class TestRandomSite:
    def test_sites_count_from_0_in_the_order_of_the_text(self):
        d = mtpc(RAND + "(rand-seed s 1) (real a (rand)) (real b (rand)) (int c (rand-int 1 6))")
        assert _sites(d) == {"a": 0, "b": 1, "c": 2}

    def test_each_copy_of_a_foreach_has_its_own_site(self):
        d = mtpc(RAND + "(rand-seed s 1) (foreach i 3 (real @'k-{i}' (rand)))")
        assert _sites(d) == {"k-0": 0, "k-1": 1, "k-2": 2}

    @SITES
    def test_the_order_in_which_the_attributes_of_a_shape_are_written(self):
        d = mtpc(RAND + "(rand-seed sd 1) (scene s (circle c (r (rand 1 2)) (x (rand 0 5))))")
        c = obj(d, "c")["attrs"]
        assert (c["r"]["bound"][2], c["x"]["bound"][2]) == (0, 1)

    def test_a_call_in_the_arguments_of_another_call_comes_after_it(self):
        d = mtpc(RAND + "(rand-seed sd 1) (real v (rand (rand 0 1) 5))")
        outer = obj(d, "v")["value"]["bound"]
        inner = outer[4] if outer[4][0] == "rand" else outer[3]
        assert outer[2] == 0 and inner[2] == 1
