"""Conformance tests of the rule records (docs/spec/data-model.md)."""

from ._shared import accepted, rule


@rule("records")
class TestRecords:
    def test_a_namespace_holds_the_attributes_it_is_declared_with(self):
        m = accepted("(namespace style (real width 2)) (real v style.width)")
        assert (m.id("style.width"), None) in m.get("v").value.deps
