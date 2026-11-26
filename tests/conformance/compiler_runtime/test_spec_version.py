"""Conformance tests of the rule spec-version (docs/spec/compiler-runtime.md)."""

from ._shared import ROOT, SPEC, SPEC_VERSION, raw_mtpc, re, rule


@rule("spec-version")
class TestSpecVersion:
    def test_every_mtpc_holds_the_version_of_this_draft(self):
        index = (SPEC / "index.md").read_text()
        (draft,) = re.findall(r"This is the draft of version (\d+) of the specification", index)
        assert raw_mtpc("")["mtpc"] == int(draft)

    def test_the_version_is_a_whole_number(self):
        version = raw_mtpc("")["mtpc"]
        assert type(version) is int and version >= 1

    def test_the_compiler_and_the_runtime_implement_the_same_version(self):
        doc_ts = (ROOT / "web" / "src" / "doc.ts").read_text()
        (runtime,) = re.findall(r"export const SPEC_VERSION = (\d+);", doc_ts)
        assert int(runtime) == SPEC_VERSION
