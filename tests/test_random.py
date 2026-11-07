"""Random values, bound to seeds (docs/reference.md, "Random values and seeds"; mtp-bjn0): a seed
is a free variable of type rand-seed, every random value is computed from a seed and the place it
is written, and rolling the dice is a write of the seed."""

import pytest
from helpers import doc, error, model
from mtpc_check import errors


def seed_of(m, name):
    """The seed a random variable's expression follows."""
    e = m.get(name).value.expr
    return e.args[1]


class TestSeeds:
    def test_a_seed_is_a_free_variable(self):
        m = model("(rand-seed dots 42)")
        v = m.get("dots").value
        assert not v.bound and v.value == 42
        assert str(v.type) == "rand-seed"

    def test_a_seed_is_a_whole_number_of_at_least_zero(self):
        error("(rand-seed dots -1)", r"-1 breaks \(>= 0\)")

    def test_a_file_with_no_seed_gets_one_named_seed_at_0(self):
        m = model("(real v (rand))")
        s = m.get("seed")
        assert s.kind == "variable" and s.value.value == 0 and str(s.value.type) == "rand-seed"

    def test_none_is_added_when_nothing_is_random(self):
        with pytest.raises(KeyError):
            model("(real v 1)").get("seed")

    def test_a_random_value_follows_the_only_seed(self):
        m = model("(rand-seed dots 7) (real v (rand))")
        v = m.get("v").value
        assert v.bound and (m.id("dots"), None) in v.deps

    def test_or_the_one_it_names(self):
        m = model("(rand-seed dots 7) (rand-seed bars 8) (real v (rand 0 1 (seed bars)))")
        assert (m.id("bars"), None) in m.get("v").value.deps
        assert (m.id("dots"), None) not in m.get("v").value.deps

    def test_with_several_it_must_name_one(self):
        error("(rand-seed dots 7) (rand-seed bars 8) (real v (rand))", "several seeds")

    def test_a_seed_is_declared_before_what_follows_it(self):
        error("(real v (rand)) (rand-seed dots 7)", "declared before")


class TestRandomFunctions:
    def test_rand(self):
        m = model("(real v (rand)) (real w (rand 2 3))")
        assert m.get("v").value.expr.op == "rand"
        assert m.get("w").value.expr.range == (2, 3)

    def test_rand_int(self):
        m = model("(int v (rand-int 1 6))")
        assert m.get("v").value.expr.op == "rand-int"
        assert m.get("v").value.expr.range == (1, 6)

    def test_pick_may_be_none(self):
        m = model("(string|none v (pick ['a' 'b']))")
        assert m.get("v").value.expr.op == "pick"
        error("(string v (pick ['a' 'b']))", "may be none")

    def test_shuffle_keeps_the_items_type(self):
        m = model("(list[int] v (shuffle [1 2 3]))")
        assert m.get("v").value.expr.op == "shuffle"

    def test_not_inside_a_function_for_now(self):
        error("(func f (real x) (+ x (rand)))", "rand inside a function")
        error("(func f ((list[int] xs)) (shuffle xs))", "shuffle inside a function")

    def test_each_is_written_with_its_place_and_its_seed(self):
        d = doc("(rand-seed dots 7) (real v (rand 2 3)) (list[int] w (shuffle [1 2 3]))")
        v = d["objects"][d["names"]["v"]]["value"]["bound"]
        assert v[0] == "rand" and v[3] == ["read", v[3][1], d["names"]["dots"], None, None]
        assert errors(d) == []


class TestRolling:
    def test_next_seed(self):
        m = model("(rand-seed dots 7) (rand-seed after (next-seed dots))")
        assert m.get("after").value.expr.op == "next-seed"

    def test_roll_dice_is_a_move_of_the_seed(self):
        m = model("(real v (rand)) (animation roll (roll-dice))")
        step = m.get("roll").data["steps"]
        assert step[0] == "move" and step[1] == (m.id("seed"), None) and step[3] == 0
        tr = m.objects[step[2]]
        assert tr.attrs["to"].expr.op == "next-seed"

    def test_roll_dice_names_a_seed(self):
        m = model("(rand-seed dots 7) (rand-seed bars 8) (animation roll (roll-dice bars))")
        assert m.get("roll").data["steps"][1] == (m.id("bars"), None)

    def test_roll_dice_takes_a_seed(self):
        error("(real k 1) (animation roll (roll-dice k))", "rand-seed")
