"""Conformance tests of the rule what-is-normative (docs/spec/compiler-runtime.md)."""

from ._shared import WORDING, Path, mtpc, rule


@rule("what-is-normative")
class TestWhatIsNormative:
    def test_no_conformance_test_checks_the_wording_of_an_error(self):
        here = Path(__file__).parent
        for path in here.glob("test_*.py"):
            text = path.read_text()
            assert not WORDING.search(text), f"{path.name} checks the wording of an error"

    def test_the_bytes_may_differ_while_the_meaning_is_the_same(self):
        # Two spellings with one meaning compile to one .mtpc, read as JSON.
        assert mtpc("(scene s (circle c (r 1) (fill #'red')))") == mtpc(
            "(scene s (circle c (fill #'red') (r 1)))"
        )
