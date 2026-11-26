"""Every rule of the drafted parts of the spec has a test, and every test cites a rule that exists.

A Python test cites a rule with the marker @pytest.mark.rule("label"), and a test of the runtime
(web/test/conformance/*.test.ts) with a describe whose name starts with "rule label:"."""

import re

from .support import ROOT, SPEC

# The parts that are drafted. The rules of the other parts get tests once those parts are drafted.
DRAFTED = [
    "overview",
    "compiler-runtime",
    "lexical",
    "grammar",
    "core",
    "evaluation",
    "data-model",
    "scope",
    "imports",
    "types",
    "binding-time",
]

RULE = re.compile(r"^`{3,}\{rule\} ([a-z0-9-]+)\s*$", re.M)
PY_CITATION = re.compile(r"""\brule\(\s*["']([a-z0-9-]+)["']\s*\)""")
TS_CITATION = re.compile(r"""\bdescribe\(\s*["'`]rule ([a-z0-9-]+):""")


def labels(parts) -> dict[str, str]:
    """Each rule label of the parts, with the part that states it."""
    found = {}
    for part in parts:
        for label in RULE.findall((SPEC / f"{part}.md").read_text(encoding="utf-8")):
            assert label not in found, f"{label} is stated in {found[label]} and in {part}"
            found[label] = part
    return found


def citations() -> dict[str, list[str]]:
    """Each label that a conformance test cites, with the files that cite it."""
    cited: dict[str, list[str]] = {}
    here = ROOT / "tests" / "conformance"
    files = [
        (p, PY_CITATION) for p in sorted(here.rglob("test_*.py")) if p.name != "test_labels.py"
    ]
    files += [(p, TS_CITATION) for p in sorted((ROOT / "web/test/conformance").rglob("*.test.ts"))]
    for path, pattern in files:
        for label in pattern.findall(path.read_text(encoding="utf-8")):
            cited.setdefault(label, []).append(path.name)
    return cited


def test_every_rule_of_a_drafted_part_has_a_test():
    cited = citations()
    missing = [f"{label} ({part})" for label, part in labels(DRAFTED).items() if label not in cited]
    assert not missing, f"rules with no test: {', '.join(missing)}"


def test_every_cited_rule_exists():
    every = labels(sorted(p.stem for p in SPEC.glob("*.md")))
    unknown = {label: files for label, files in citations().items() if label not in every}
    assert not unknown, f"tests cite rules that the spec does not state: {unknown}"


def test_the_check_finds_the_rules_and_the_citations():
    assert len(labels(DRAFTED)) > 50
    assert "keywords" in citations()
