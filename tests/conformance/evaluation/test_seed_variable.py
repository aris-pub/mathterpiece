"""Conformance tests of the rule seed-variable (docs/spec/evaluation.md)."""

from ._shared import RAND, SEED_SIGN, accepted, compile_error, rule


@rule("seed-variable")
class TestSeedVariable:
    def test_a_random_function_follows_its_seed(self):
        m = accepted(RAND + "(rand-seed a 1) (rand-seed b 2) (real v (rand 0 1 (seed b)))")
        assert (m.id("b"), None) in m.get("v").value.deps
        assert (m.id("a"), None) not in m.get("v").value.deps

    def test_a_const_variable_is_not_a_seed(self):
        compile_error(RAND + "(rand-seed s 3 (const)) (real v (rand))")

    @SEED_SIGN
    def test_a_seed_is_any_int(self):
        accepted(RAND + "(rand-seed s -1) (real v (rand))")

    def test_with_several_seeds_a_random_function_names_one(self):
        compile_error(RAND + "(rand-seed a 1) (rand-seed b 2) (real v (rand))")
