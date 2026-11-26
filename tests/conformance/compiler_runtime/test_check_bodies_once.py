"""Conformance tests of the rule check-bodies-once (docs/spec/compiler-runtime.md)."""

from ._shared import REJECTION, STEPS, accepted, compile_error, in_folder, pytest, rule


@rule("check-bodies-once")
class TestProveBodiesOnce:
    def test_a_motif_body_is_proved_for_every_value_of_its_parameters(self):
        compile_error("(motif dot ((real k)) (circle_ (r (/ 1 k))))")

    def test_a_constraint_leaves_out_the_other_values(self):
        accepted("(motif dot ((real k 1 (>= 1))) (circle_ (r (/ 1 k))))")

    def test_a_function_body_is_proved_with_no_call(self):
        compile_error("(func[real] f ((real x)) (/ 1 x))")

    def test_an_imported_motif_is_proved_in_its_file(self, tmp_path):
        lib = {"lib.mtp": "(motif dot ((real k)) (circle_ (r (/ 1 k))))\n"}
        with pytest.raises(REJECTION):
            in_folder(tmp_path, lib, "(import lib)\n")

    @STEPS
    def test_a_foreach_body_is_proved_once_for_its_range(self):
        accepted("(scene s (foreach i 3 (circle_ (r (or? (/ 1 i) 1)))))")
