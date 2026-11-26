"""Conformance tests of the rule foreach-copies (docs/spec/binding-time.md)."""

from ._shared import free, mtpc, obj, rule


@rule("foreach-copies")
class TestForeachCopies:
    def test_one_copy_per_item_of_a_known_list(self):
        d = mtpc("(scene s (foreach k {1 2 3} (circle @'c-{k}' (r k))))")
        assert [free(d, f"c-{k}", "r") for k in (1, 2, 3)] == [1, 2, 3]
        assert len(obj(d, "s")["members"]) == 3

    def test_one_copy_per_item_of_a_list_whose_items_are_known_only_while_drawing(self):
        d = mtpc("(real a 1) (list[real] xs {a 0 1}) (scene s (foreach k xs (circle_ (r 1))))")
        assert len(obj(d, "s")["members"]) == 3
