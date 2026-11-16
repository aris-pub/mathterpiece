"""Random values, bound to seeds (docs/spec/evaluation.md, "Randomness"; mtp-bjn0): a seed is a
free variable of type rand-seed, every random value is computed from a seed and the place it is
written, and rolling the dice is a write of the seed. The author, 2026-11-16: every random name
comes from the standard library file rand, which names the compiler's primitives with
(primitive N), and roll-dice is a choreo written in rand.mtp (docs/spec/stdlib.md)."""

import json
import tempfile
from pathlib import Path

import pytest
from helpers import doc, error, model
from mtpc_check import errors

from mathterpiece import compiler
from mathterpiece.compiler import CompileError, compile_source
from mathterpiece.mtpc import write

RAND = "(import rand rand rand-int pick shuffle next-seed roll-dice)\n"


def in_file(src, **others):
    """The model of a source compiled from a file, with other files beside it."""
    folder = Path(tempfile.mkdtemp())
    for name, text in others.items():
        (folder / f"{name}.mtp").write_text(text)
    path = folder / "fig.mtp"
    path.write_text(src)
    return compile_source(src, path=path)


def mtpc_of(m):
    return json.loads(write(m))


class TestSeeds:
    def test_a_seed_is_a_free_variable(self):
        m = model("(rand-seed dots 42)")
        v = m.get("dots").value
        assert not v.bound and v.value == 42
        assert str(v.type) == "rand-seed"

    def test_a_seed_is_a_whole_number_of_at_least_zero(self):
        error("(rand-seed dots -1)", r"-1 breaks \(>= 0\)")

    def test_the_standard_seed_follows_a_file_with_none_of_its_own(self):
        m = in_file("(import rand rand) (real v (rand))")
        s = m.get("rand.seed")
        assert s.kind == "variable" and s.value.value == 0 and str(s.value.type) == "rand-seed"
        assert (m.id("rand.seed"), None) in m.get("v").value.deps

    def test_and_the_file_imported_whole(self):
        m = in_file("(import rand) (real v (rand.rand))")
        assert (m.id("rand.seed"), None) in m.get("v").value.deps

    def test_no_file_has_a_seed_it_did_not_ask_for(self):
        with pytest.raises(KeyError):
            in_file("(real v 1)").get("seed")
        with pytest.raises(KeyError):
            in_file("(import rand) (real v 1)").get("rand.seed")

    def test_a_random_value_follows_the_only_seed_the_file_declares(self):
        m = model(RAND + "(rand-seed dots 7) (real v (rand))")
        v = m.get("v").value
        assert v.bound and (m.id("dots"), None) in v.deps
        # The standard seed is put in by the import, but nothing uses it, so the .mtpc does not
        # hold it.
        assert "rand.seed" not in mtpc_of(m)["names"]

    def test_or_the_one_it_names(self):
        m = model(RAND + "(rand-seed dots 7) (rand-seed bars 8) (real v (rand 0 1 (seed bars)))")
        assert (m.id("bars"), None) in m.get("v").value.deps
        assert (m.id("dots"), None) not in m.get("v").value.deps

    def test_with_several_it_must_name_one(self):
        error(RAND + "(rand-seed dots 7) (rand-seed bars 8) (real v (rand))", "several seeds")

    def test_the_standard_seed_named_and_one_of_its_own_are_two(self):
        error("(import rand rand seed) (rand-seed dots 7) (real v (rand))", "several seeds")
        with pytest.raises(CompileError, match="several seeds"):
            in_file("(import rand) (rand-seed dots 7) (real v (rand.rand))")

    def test_a_seed_of_another_file_imported_by_name(self):
        m = in_file(RAND + "(import house hs) (real v (rand))", house="(rand-seed hs 3)")
        assert (m.id("house.hs"), None) in m.get("v").value.deps

    def test_a_seed_declared_after_the_random_value(self):
        error(RAND + "(real v (rand)) (rand-seed dots 7)", "dots is declared after")

    def test_a_const_seed(self):
        error(RAND + "(rand-seed s 3 (const)) (real v (rand))", "s is const")

    def test_a_const_one_beside_a_seed(self):
        m = model(RAND + "(rand-seed s 3 (const)) (rand-seed t 4) (real v (rand))")
        assert (m.id("t"), None) in m.get("v").value.deps

    def test_a_motif_of_another_file_follows_that_files_seed(self):
        house = "(import rand rand) (rand-seed hs 3) (motif dot () (circle c (r (rand 1 2))))"
        m = in_file("(import house dot) (rand-seed mine 1) (scene s (dot d))", house=house)
        deps = m.get("d.c").attrs["r"].deps
        assert (m.id("house.hs"), None) in deps and (m.id("mine"), None) not in deps

    def test_a_motif_of_a_file_with_no_seed_follows_the_seed_of_rand(self):
        house = "(import rand rand) (motif dot () (circle c (r (rand 1 2))))"
        m = in_file("(import house dot) (rand-seed mine 1) (scene s (dot d))", house=house)
        deps = m.get("d.c").attrs["r"].deps
        assert (m.id("rand.seed"), None) in deps and (m.id("mine"), None) not in deps


class TestRandomFunctions:
    def test_rand(self):
        m = model(RAND + "(rand-seed s 0) (real v (rand)) (real w (rand 2 3))")
        assert m.get("v").value.expr.op == "rand"
        assert m.get("w").value.expr.range == (2, 3)

    def test_rand_int(self):
        m = model(RAND + "(rand-seed s 0) (int v (rand-int 1 6))")
        assert m.get("v").value.expr.op == "rand-int"
        assert m.get("v").value.expr.range == (1, 6)

    def test_by_the_name_of_the_file(self):
        m = in_file("(import rand) (int v (rand.rand-int 1 6))")
        assert m.get("v").value.expr.op == "rand-int"

    def test_each_call_has_its_own_site(self):
        d = doc(RAND + "(rand-seed s 0) (int a (rand-int 1 6)) (int b (rand-int 1 6))")
        a = d["objects"][d["names"]["a"]]["value"]["bound"]
        b = d["objects"][d["names"]["b"]]["value"]["bound"]
        assert (a[2], b[2]) == (0, 1)

    def test_the_same_mtpc_as_before(self):
        # A source that imports the names compiles to what the built-ins compiled to.
        d = doc(RAND + "(rand-seed dots 7) (real v (rand 2 3)) (list[int] w (shuffle [1 2 3]))")
        v = d["objects"][d["names"]["v"]]["value"]["bound"]
        assert v[0] == "rand" and v[3] == ["read", v[3][1], d["names"]["dots"], None, None]
        assert errors(d) == []

    def test_rand_times_a_number_is_not_none(self):
        # mtp-gvrf.13: with bounds not known when compiling, the range of rand reached the
        # largest real, so a product of it could overflow and was inferred as maybe none. A
        # value with no upper limit of its own stops at 10^150, as sum does (mtp-gvrf.8).
        src = RAND + "(rand-seed s 0) (real a 0) (real b 1)"
        m = model(f"{src} (real v (rand a b)) (real x (* (rand a b) 8))")
        assert m.get("v").value.expr.range == (-1e150, 1e150)
        assert m.get("x").value.expr.range == (-1e150, 1e150)
        assert model(f"{src} (real x (* (rand 0 10) 8))").get("x").value.expr.range == (0, 80)

    def test_rand_int_times_a_number_is_not_none(self):
        src = RAND + "(rand-seed s 0) (int a 0) (int b 1)"
        m = model(f"{src} (int v (rand-int a b)) (int x (* (rand-int a b) 8))")
        assert m.get("v").value.expr.range == (-1e150, 1e150)
        assert m.get("x").value.expr.range == (-1e150, 1e150)
        assert model(f"{src} (int x (* (rand-int 1 6) 8))").get("x").value.expr.range == (8, 48)

    def test_pick_may_be_none(self):
        m = model(RAND + "(rand-seed s 0) (string|none v (pick ['a' 'b']))")
        assert m.get("v").value.expr.op == "pick"
        error(RAND + "(rand-seed s 0) (string v (pick ['a' 'b']))", "may be none")

    def test_shuffle_keeps_the_items_type(self):
        m = model(RAND + "(rand-seed s 0) (list[int] v (shuffle [1 2 3]))")
        assert m.get("v").value.expr.op == "shuffle"

    def test_not_inside_a_function_for_now(self):
        error(RAND + "(rand-seed s 0) (func f (real x) (+ x (rand)))", "rand inside a function")
        error(
            RAND + "(rand-seed s 0) (func f ((list[int] xs)) (shuffle xs))",
            "shuffle inside a function",
        )

    def test_a_primitive_is_only_called(self):
        error(
            RAND + "(rand-seed s 0) (list v (map [1 2] rand))",
            r"rand is only called, as \(rand …\)",
        )

    def test_a_let_name_hides_it(self):
        m = model(RAND + "(rand-seed s 0) (real v (let ((rand (fn ((real x)) (* 2 x)))) (rand 3)))")
        assert m.get("v").value.value == 6


class TestWhereTheNamesComeFrom:
    @pytest.mark.parametrize(
        "src, name",
        [
            ("(rand-seed s 0) (int v (rand-int 1 6))", "rand-int"),
            ("(rand-seed s 0) (real v (rand))", "rand"),
            ("(rand-seed s 0) (string|none v (pick ['a']))", "pick"),
            ("(rand-seed s 0) (list[int] v (shuffle [1 2]))", "shuffle"),
            ("(rand-seed s 0) (rand-seed t (next-seed s))", "next-seed"),
            ("(real v seed)", "seed"),
            ("(rand-seed s 0) (animation a (roll-dice s))", "roll-dice"),
            ("(rand-seed s 0) (button b (roll-dice s))", "roll-dice"),
        ],
    )
    def test_a_name_of_rand_that_the_file_does_not_import(self, src, name):
        error(src, rf": {name} comes from the standard library: \(import rand {name}\)$")

    @pytest.mark.parametrize(
        "src, name",
        [
            ("(int v (rand.rand-int 1 6))", "rand-int"),
            ("(real v rand.seed)", "seed"),
            ("(animation a (rand.roll-dice))", "roll-dice"),
            ("(button b (rand.roll-dice))", "roll-dice"),
        ],
    )
    def test_a_name_of_rand_by_the_name_of_the_file(self, src, name):
        error(src, rf": rand.{name} comes from the standard library: \(import rand\)$")

    def test_a_name_that_another_import_does_not_give(self):
        error(
            "(import rand rand) (int v (rand-int 1 6))",
            r"rand-int comes from the standard library: \(import rand rand-int\)",
        )

    def test_any_other_unknown_name_is_as_before(self):
        error("(real v (nope 1))", "unknown function 'nope'")
        error("(real v nope)", "unknown name 'nope'")


class TestThePrimitiveForm:
    def test_a_source_holds_none(self):
        error("(primitive rand)", r"only a file of the standard library holds \(primitive …\)")

    def test_nor_a_file_it_imports(self):
        with pytest.raises(CompileError, match="only a file of the standard library holds"):
            in_file("(import lib r) (real v 1)", lib="(primitive rand)")

    def test_a_file_of_the_standard_library_does(self, tmp_path, monkeypatch):
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "dice.mtp").write_text(
            "(primitive rand-int doc@'An int from lo to hi.') (rand-seed seed 0)"
        )
        monkeypatch.setattr(compiler, "STDLIB", lib)
        m = in_file("(import dice rand-int) (rand-seed s 1) (int v (rand-int 1 6))")
        assert m.get("v").value.expr.op == "rand-int"
        # Only the seed of rand.mtp follows a file that has none of its own.
        with pytest.raises(CompileError, match="a random value follows a seed"):
            in_file("(import dice rand-int) (int v (rand-int 1 6))")

    @pytest.mark.parametrize(
        "text, match",
        [
            (
                "(primitive sqrt)",
                "primitive names one of rand, rand-int, pick, shuffle and next-seed",
            ),
            ("(primitive)", r"primitive is \(primitive name\)"),
            ("(primitive rand 3)", r"primitive is \(primitive name\)"),
            ("(primitive rand) (primitive rand)", "'rand' is already declared"),
        ],
    )
    def test_what_it_holds(self, text, match, tmp_path, monkeypatch):
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "dice.mtp").write_text(text)
        monkeypatch.setattr(compiler, "STDLIB", lib)
        with pytest.raises(CompileError, match=match):
            in_file("(import dice) (real v 1)")

    def test_an_import_from_a_string_reads_the_standard_library(self):
        # A source compiled with no file of its own still imports the standard library.
        assert model("(import math clamp) (real v (clamp 5 0 2))").get("v").value.value == 2


class TestRolling:
    def test_next_seed(self):
        m = model(RAND + "(rand-seed dots 7) (rand-seed after (next-seed dots))")
        assert m.get("after").value.expr.op == "next-seed"

    def test_roll_dice_is_a_move_of_the_seed(self):
        m = in_file("(import rand roll-dice) (animation roll (roll-dice))")
        step = m.get("roll").data["steps"]
        assert step[0] == "move" and step[1] == (m.id("rand.seed"), None) and step[3] == 0
        tr = m.objects[step[2]]
        assert tr.attrs["to"].expr.op == "next-seed"

    def test_by_the_name_of_the_file(self):
        m = in_file("(import rand) (animation roll (rand.roll-dice))")
        assert m.get("roll").data["steps"][1] == (m.id("rand.seed"), None)

    def test_roll_dice_rolls_the_only_seed_the_file_declares(self):
        m = model(RAND + "(rand-seed dots 7) (animation roll (roll-dice))")
        assert m.get("roll").data["steps"][1] == (m.id("dots"), None)
        assert "rand.seed" not in mtpc_of(m)["names"]

    def test_roll_dice_names_a_seed(self):
        m = model(RAND + "(rand-seed dots 7) (rand-seed bars 8) (animation roll (roll-dice bars))")
        assert m.get("roll").data["steps"][1] == (m.id("bars"), None)

    def test_with_several_seeds_it_names_one(self):
        error(
            RAND + "(rand-seed dots 7) (rand-seed bars 8) (animation roll (roll-dice))", "several"
        )

    def test_roll_dice_takes_a_seed(self):
        error(RAND + "(real k 1) (animation roll (roll-dice k))", "rand-seed")

    def test_roll_dice_of_a_number(self):
        error(
            RAND + "(animation roll (roll-dice 3))",
            r"the argument for s is the name of a seed, as in \(roll-dice dots\)",
        )

    def test_a_choreo_of_ones_own_moves_the_seed_it_is_given(self):
        roll = "(choreo twice ((rand-seed s)) (set s (next-seed s)) (set s (next-seed s)))"
        m = model(RAND + f"(rand-seed dots 7) {roll} (animation a (twice dots))")
        steps = m.get("a").data["steps"]
        assert steps[0] == "in-order" and steps[1][1] == steps[2][1] == (m.id("dots"), None)

    def test_roll_dice_on_a_control(self):
        a = model(RAND + "(rand-seed dots 7) (button b (roll-dice))")
        b = model(
            RAND + "(rand-seed dots 7) (button b (move dots (to (next-seed dots)) (duration 0)))"
        )
        assert write(a) == write(b)

    def test_the_same_mtpc_as_the_move(self):
        a = model(RAND + "(rand-seed s 1) (animation r (roll-dice s))")
        b = model(RAND + "(rand-seed s 1) (animation r (move s (to (next-seed s)) (duration 0)))")
        assert write(a) == write(b)
