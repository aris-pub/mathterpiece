"""Conformance tests of the rule schema-strength (docs/spec/compiler-runtime.md)."""

from ._shared import FIGURE, LISTENERS, SPEC_VERSION, _listener, raw_mtpc, rule, schema_errors


@rule("schema-strength")
class TestSchemaStrength:
    def test_a_valid_mtpc_matches(self):
        assert schema_errors(raw_mtpc(FIGURE)) == []

    def test_another_version_does_not_match(self):
        d = raw_mtpc(FIGURE)
        d["mtpc"] = SPEC_VERSION + 1
        assert schema_errors(d)

    def test_an_unknown_kind_of_object_does_not_match(self):
        d = raw_mtpc(FIGURE)
        d["objects"][0]["kind"] = "no-such-kind"
        assert schema_errors(d)

    def test_a_reference_to_no_object_is_not_an_int(self):
        d = raw_mtpc(FIGURE)
        d["names"]["k"] = "zero"
        assert schema_errors(d)

    def test_a_listener_on_a_shape_names_one_view_in_in(self):
        d = raw_mtpc(LISTENERS)
        assert schema_errors(d) == []
        v, w = d["names"]["v"], d["names"]["w"]
        for kind in ("on-click", "on-enter", "on-drag", "on-show"):
            listener = _listener(d, kind)
            listener["in"] = [v, w]
            assert schema_errors(d), kind
            del listener["in"]
            assert schema_errors(d), kind
            listener["in"] = [v]

    def test_an_on_pointermove_names_one_view_in_in_only_on_a_shape(self):
        d = raw_mtpc(LISTENERS)
        moves = [o for o in d["objects"] if o["kind"] == "on-pointermove"]
        (on_shape,) = [o for o in moves if o["shape"] is not None]
        (on_canvas,) = [o for o in moves if o["shape"] is None]
        v = d["names"]["v"]
        del on_shape["in"]
        assert schema_errors(d)
        on_shape["in"] = [v]
        on_canvas["in"] = [v]
        assert schema_errors(d)

    def test_a_listener_on_its_own_view_has_no_in(self):
        d = raw_mtpc(LISTENERS)
        _listener(d, "on-view")["in"] = [d["names"]["v"]]
        assert schema_errors(d)
