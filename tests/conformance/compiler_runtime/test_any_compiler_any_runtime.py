"""Conformance tests of the rule any-compiler-any-runtime (docs/spec/compiler-runtime.md)."""

from ._shared import ROOT, SPEC_VERSION, compiled, json, pytest, rule, schema_errors


@rule("any-compiler-any-runtime")
class TestAnyCompilerAnyRuntime:
    """Another compiler or runtime can only rely on what the format defines, so every .mtpc that
    this compiler writes must match the schema of its version, which the runtime implements."""

    @pytest.mark.parametrize(
        "src", sorted((ROOT / "docs" / "spec" / "pages").glob("*/*.mtp")), ids=lambda p: p.name
    )
    def test_the_mtpc_of_each_example_page_matches_the_schema(self, src):
        doc = json.loads(compiled(src.read_text(encoding="utf-8"), src))
        assert schema_errors(doc) == []
        assert doc["mtpc"] == SPEC_VERSION
