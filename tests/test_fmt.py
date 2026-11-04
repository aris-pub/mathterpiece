"""mtp fmt (docs/data-model.md, "The mtp command"): each line indented as the Emacs mode indents
it, trailing spaces dropped, at most one blank line in a row, and nothing else changed."""

import re
from pathlib import Path

import pytest

from mathterpiece.fmt import INDENT, NAMED, layout
from mathterpiece.parse import parse

ROOT = Path(__file__).parent.parent
FILES = sorted([*ROOT.glob("examples/*.mtp"), *ROOT.glob("tests/shared/*.mtp")])


def test_a_forms_positional_arguments_go_4_in_and_its_body_2():
    src = "(canvas\nview\n(x 1)\ns)\n"
    assert layout(src) == "(canvas\n    view\n  (x 1)\n  s)\n"


def test_the_body_of_a_shape():
    src = "(scene s\n(circle c (r 1)\n(fill 'red')))\n"
    assert layout(src) == "(scene s\n  (circle c (r 1)\n    (fill 'red')))\n"


def test_a_form_with_no_name_has_one_positional_fewer():
    assert layout("(scene s\n(circle_\n(r 1)))\n") == "(scene s\n  (circle_\n    (r 1)))\n"


def test_a_form_with_a_list_where_its_name_would_be():
    # As an animation written inside a control: (animation (in-order …)) has no name.
    src = "(play p\n(animation\n(in-order a b)))\n"
    assert layout(src) == "(play p\n  (animation\n    (in-order a b)))\n"


def test_a_call_lines_up_with_its_first_argument():
    assert layout("(real v (+ a\nb\n   c))\n") == "(real v (+ a\n           b\n           c))\n"


def test_a_call_with_no_argument_on_its_line():
    # As the Emacs mode does: under the head.
    assert layout("(real v (max\n1 2))\n") == "(real v (max\n         1 2))\n"


def test_a_list_lines_up_inside_its_bracket():
    assert layout("(list xs [1 2\n3])\n") == "(list xs [1 2\n          3])\n"


def test_an_index_is_not_an_item():
    src = "(real v (+ g[0]\nh))\n"
    assert layout(src) == "(real v (+ g[0]\n           h))\n"


def test_comments_are_indented_as_code_and_kept():
    src = "(scene s\n; a comment\n(circle c))   \n"
    assert layout(src) == "(scene s\n  ; a comment\n  (circle c))\n"


def test_blank_lines_and_the_end_of_the_file():
    assert layout("(real a 1)\n\n\n\n(real b 2)") == "(real a 1)\n\n(real b 2)\n"


def test_brackets_and_semicolons_in_strings_count_for_nothing():
    src = "(scene s\n(text t '(; [')\n(circle c))\n"
    assert layout(src) == "(scene s\n  (text t '(; [')\n  (circle c))\n"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_every_file_keeps_its_meaning_and_formats_once(path):
    src = path.read_text()
    out = layout(src)
    assert parse(out) == parse(src)
    assert layout(out) == out


def _emacs(src: str, tmp_path: Path) -> str:
    """src as the Emacs mode indents it."""
    import shutil
    import subprocess

    if shutil.which("emacs") is None:
        pytest.skip("emacs is not installed")
    path, out = tmp_path / "in.mtp", tmp_path / "out.mtp"
    path.write_text(src)
    code = (
        f'(progn (find-file "{path}") (mtp-mode) (indent-region (point-min) (point-max))'
        f' (delete-trailing-whitespace) (write-region (point-min) (point-max) "{out}"))'
    )
    subprocess.run(
        ["emacs", "--batch", "-L", str(ROOT / "editors"), "-l", "mtp-mode.el", "--eval", code],
        check=True,
        capture_output=True,
    )
    return out.read_text()


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_every_file_is_indented_as_emacs_indents_it(path, tmp_path):
    emacs = [line.rstrip() for line in _emacs(path.read_text(), tmp_path).split("\n")]
    ours = [line.rstrip() for line in layout(path.read_text()).split("\n")]
    # fmt also drops extra blank lines, which Emacs keeps; compare the lines with text.
    assert [x for x in ours if x] == [x for x in emacs if x]


# A list is data, not a call: its later lines go under its first item, as do those of a form
# whose head is not a name.
@pytest.mark.parametrize(
    "src, want",
    [
        (
            "(list[color] hues [terracotta teal saffron plum\n(mix terracotta paper 0.45)])\n",
            "(list[color] hues [terracotta teal saffron plum\n"
            "                   (mix terracotta paper 0.45)])\n",
        ),
        ("(list xs [1 2\n3])\n", "(list xs [1 2\n          3])\n"),
        ("(list xs [(f a) b\nc])\n", "(list xs [(f a) b\n          c])\n"),
        ("(list xs [\na b\nc])\n", "(list xs [\n          a b\n          c])\n"),
        ("(real v ((f a) b\nc))\n", "(real v ((f a) b\n         c))\n"),
    ],
)
def test_a_list_lines_up_under_its_first_item_in_fmt_and_emacs(src, want, tmp_path):
    assert layout(src) == want
    assert _emacs(src, tmp_path) == want


def test_the_table_is_the_emacs_modes():
    el = (ROOT / "editors/mtp-mode.el").read_text()
    pairs = dict(re.findall(r'\("([a-z-]+)" \. (\d+)\)', el))
    assert {k: int(v) for k, v in pairs.items()} == INDENT
    named = re.search(r"mtp-mode--named\s+'\((.*?)\)", el, re.S)
    assert named is not None
    assert set(re.findall(r'"([a-z-]+)"', named.group(1))) == NAMED
