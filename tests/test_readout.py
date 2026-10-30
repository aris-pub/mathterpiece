import pytest
from helpers import with_scene

from mathterpiece.compiler import CompileError, compile_model
from mathterpiece.export import to_json
from mathterpiece.model import Bound, Free, Readout


def scene(src):
    return compile_model(with_scene(src))


def readout(model, name) -> Readout:
    found = model[name]
    assert isinstance(found, Readout)
    return found


class TestReadout:
    def test_reads_the_scene(self):
        m = scene("(real 'k' 2) (circle 'c') (readout 'r' $'k = {k:.1f}, x = {c.x}')")
        assert isinstance(readout(m, "r").value, Bound)
        assert readout(m, "r") in m.views

    def test_known_text(self):
        assert readout(scene("(readout 'r' 'hello')"), "r").value == Free("hello")

    def test_any_string_expression(self):
        m = scene("(real 'k' 2) (readout 'r' (if (> k 1) 'big' 'small'))")
        assert isinstance(readout(m, "r").value, Bound)

    @pytest.mark.parametrize(
        "src, match",
        [
            ("(readout 'r' 3)", "str"),
            ("(scene 'w' (readout 'r' 'a'))", "outside the scene"),
        ],
    )
    def test_invalid(self, src, match):
        with pytest.raises(CompileError, match=match):
            scene(src)

    def test_export(self):
        doc = to_json(scene("(real 'k' 2) (readout 'r' $'{k:.1f}')"))
        r = doc["objects"][doc["names"]["r"]]
        k = doc["names"]["k"]
        assert r["kind"] == "readout"
        assert r["attrs"]["value"] == ["str", ["show", ["read", k, "value"], "real", ".1f"]]
