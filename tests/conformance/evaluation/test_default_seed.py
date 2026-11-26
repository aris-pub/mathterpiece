"""Conformance tests of the rule default-seed (docs/spec/evaluation.md)."""

from ._shared import RAND, accepted, compile_error, in_folder, rule, same_meaning


@rule("default-seed")
class TestDefaultSeed:
    def test_the_only_seed_of_the_file_scope(self):
        m = accepted(RAND + "(rand-seed a 1) (real v (rand))")
        assert (m.id("a"), None) in m.get("v").value.deps

    def test_a_seed_that_an_import_gives(self, tmp_path):
        (tmp_path / "lib.mtp").write_text("(rand-seed hs 3)")
        m = accepted(RAND + "(import lib hs) (real v (rand))", tmp_path / "a.mtp")
        assert (m.id("lib.hs"), None) in m.get("v").value.deps

    def test_with_no_variable_of_type_rand_seed_the_seed_of_rand(self):
        m = accepted(RAND + "(real v (rand))")
        assert (m.id("rand.seed"), None) in m.get("v").value.deps

    def test_a_const_variable_of_type_rand_seed_is_not_a_seed(self):
        compile_error(RAND + "(rand-seed s 3 (const)) (real v (rand))")
        m = accepted(RAND + "(rand-seed s 3 (const)) (rand-seed t 4) (real v (rand))")
        assert (m.id("t"), None) in m.get("v").value.deps

    def test_a_seed_declared_after_the_use(self):
        compile_error(RAND + "(real v (rand)) (rand-seed a 1)")

    def test_several_seeds(self):
        compile_error(RAND + "(rand-seed a 1) (rand-seed b 2) (real v (rand))")

    def test_the_seed_of_rand_and_another(self, tmp_path):
        compile_error("(import rand) (rand-seed a 1) (real v (rand.rand))", tmp_path / "a.mtp")

    def test_a_random_function_follows_the_default_seed(self):
        same_meaning(
            RAND + "(rand-seed s 1) (real v (rand 0 1))",
            RAND + "(rand-seed s 1) (real v (rand 0 1 (seed s)))",
        )

    def test_by_any_name_that_an_import_gives(self, tmp_path):
        a = in_folder(tmp_path, {}, "(import rand) (real v (rand.rand 0 1))")
        assert (a.id("rand.seed"), None) in a.get("v").value.deps
        compile_error("(import rand) (rand-seed s 1) (real v (rand.rand 0 1))", tmp_path / "a.mtp")

    def test_a_seed_of_a_declared_type(self):
        m = accepted(RAND + "(type dice rand-seed) (dice s 1) (real v (rand 0 1))")
        assert (m.id("s"), None) in m.get("v").value.deps

    def test_with_no_seed_the_seed_of_rand(self, tmp_path):
        same_meaning(
            "(import rand rand) (real v (rand 0 1))",
            "(import rand rand seed) (real v (rand 0 1 (seed seed)))",
            tmp_path / "a.mtp",
        )

    def test_roll_dice_with_no_seed(self):
        same_meaning(
            RAND + "(rand-seed s 1) (button b (animation (roll-dice)))",
            RAND + "(rand-seed s 1) (button b (animation (roll-dice s)))",
        )

    def test_roll_dice_with_no_seed_by_the_name_of_the_file(self, tmp_path):
        same_meaning(
            "(import rand) (button b (animation (rand.roll-dice)))",
            "(import rand) (button b (animation (rand.roll-dice rand.seed)))",
            tmp_path / "a.mtp",
        )

    def test_roll_dice_is_its_choreo(self):
        same_meaning(
            RAND + "(rand-seed s 1) (button b (animation (roll-dice s)))",
            RAND + "(rand-seed s 1) (button b (animation (set s (next-seed s))))",
        )

    def test_roll_dice_needs_a_seed(self):
        compile_error(RAND + "(real k 1) (button b (animation (roll-dice k)))")

    def test_roll_dice_with_several_seeds(self):
        compile_error(RAND + "(rand-seed s 1) (rand-seed t 2) (button b (animation (roll-dice)))")
