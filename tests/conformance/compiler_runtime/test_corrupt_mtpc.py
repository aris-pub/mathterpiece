"""Conformance tests of the rule corrupt-mtpc (docs/spec/compiler-runtime.md)."""

from ._shared import EXAMPLES, _bound_slots, _walk, mtpc, pytest, rule


@rule("corrupt-mtpc")
class TestCorruptMtpc:
    @pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
    def test_the_compiler_writes_no_corrupt_mtpc(self, path):
        d = mtpc(path.read_text(), path=path)
        found = {"reads": [], "calls": []}
        _walk(d["objects"], found)
        _walk(d["functions"], found)
        assert all(0 <= i < len(d["objects"]) for i, _ in found["reads"])
        assert all(0 <= i < len(d["functions"]) for i in found["calls"])
        for o, slot in _bound_slots(d):
            # An expression that reads nothing is known when compiling, so it is folded.
            assert slot["deps"], f"{o.get('name')} is bound but reads nothing"
            found = {"reads": [], "calls": []}
            _walk(slot["bound"], found)
            # The position of a group is read through its translate, so a read of an object
            # needs some attribute of that object in deps, and not always the one read.
            read_objects = {i for i, _ in slot["deps"]}
            for i, a in found["reads"]:
                assert i in read_objects, f"{o.get('name')} reads {(i, a)} without it in deps"
