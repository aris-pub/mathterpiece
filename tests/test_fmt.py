"""mtp fmt (docs/data-model.md, "The mtp command"): each line indented as the Emacs mode indents
it, trailing spaces dropped, at most one blank line in a row, (doc 'text') written doc@'text',
and nothing else changed."""

import re
import shutil
from pathlib import Path

import pytest

from mathterpiece.fmt import INDENT, KEYWORDS, NAMED, NO_BODY, layout
from mathterpiece.parse import parse

ROOT = Path(__file__).parent.parent
FILES = sorted(
    [
        *ROOT.glob("examples/*.mtp"),
        *ROOT.glob("tests/shared/*.mtp"),
        *ROOT.glob("mathterpiece/stdlib/*.mtp"),
    ]
)


def test_a_forms_positional_arguments_and_keywords_go_4_in_and_its_body_2():
    src = "(canvas\nview\n(x 1)\ns)\n"
    assert layout(src) == "(canvas\n    view\n    (x 1)\n  s)\n"


# A keyword argument on a line of its own goes 4 in, like a positional argument, so it reads
# apart from the body at 2. A form with no body has nothing but arguments, all at 4.
@pytest.mark.parametrize(
    "src, want",
    [
        (
            "(scene s\n(background paper)\n(circle c))\n",
            "(scene s\n    (background paper)\n  (circle c))\n",
        ),
        (
            "(scene s\n(circle c (r 1)\n(fill 'red')))\n",
            "(scene s\n  (circle c (r 1)\n      (fill 'red')))\n",
        ),
        (
            "(group g\n(defaults (fill red)\n(stroke blue))\n(circle c))\n",
            "(group g\n    (defaults (fill red)\n        (stroke blue))\n  (circle c))\n",
        ),
        (
            "(canvas view\n(width 2)\n(zoom true)\n(when on s)\nt\n(pan true))\n",
            "(canvas view\n    (width 2)\n    (zoom true)\n  (when on s)\n  t\n    (pan true))\n",
        ),
        (
            "(animation a\n(loop)\n(move c.r 2\n(duration 1))\n(move c.r 1))\n",
            "(animation a\n    (loop)\n  (move c.r 2\n      (duration 1))\n  (move c.r 1))\n",
        ),
        (
            "(in-order\n(ease 'linear')\n(at-once (duration 2)\n(move a 1)))\n",
            "(in-order\n    (ease 'linear')\n  (at-once (duration 2)\n    (move a 1)))\n",
        ),
        (
            "(step 'Grow'\n(defaults (duration 1))\n(move a 1)\n(wait 1))\n",
            "(step 'Grow'\n    (defaults (duration 1))\n  (move a 1)\n  (wait 1))\n",
        ),
        (
            "(motif dial ((real v))\n(x 1)\n(circle c))\n",
            "(motif dial ((real v))\n  (x 1)\n  (circle c))\n",
        ),
        ("(real v 1\n(>= 0))\n", "(real v 1\n    (>= 0))\n"),
        ("(slider s v\n(from 0)\n(to 1))\n", "(slider s v\n    (from 0)\n    (to 1))\n"),
        ("(if a\nb\nc)\n", "(if a\n    b\n  c)\n"),
        ("(foreach i 2\n(circle_))\n", "(foreach i 2\n  (circle_))\n"),
        (
            "(foreach ((i 2)\n(j 3))\n(circle_))\n",
            "(foreach ((i 2)\n          (j 3))\n  (circle_))\n",
        ),
    ],
)
def test_keyword_arguments_go_4_in_in_fmt_and_emacs(src, want, tmp_path):
    assert layout(src) == want
    assert _emacs(src, tmp_path) == want


def test_the_members_of_a_namespace(tmp_path):
    src = "(namespace theme\n(color ink 'navy')\n(namespace accents\n(color warm 'red')))\n"
    want = (
        "(namespace theme\n  (color ink 'navy')\n  (namespace accents\n    (color warm 'red')))\n"
    )
    assert layout(src) == want
    if shutil.which("emacs") is not None:
        assert _emacs(src, tmp_path) == want


def test_a_form_with_no_name_has_one_positional_fewer():
    assert layout("(scene s\n(circle_\n(r 1)))\n") == "(scene s\n  (circle_\n      (r 1)))\n"


def test_a_form_with_a_list_where_its_name_would_be():
    # As an animation written inside a control: (animation (in-order …)) has no name.
    src = "(play p\n(animation\n(in-order a b)))\n"
    assert layout(src) == "(play p\n    (animation\n      (in-order a b)))\n"


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


# The author, 2026-11-06: a docstring goes 2 in, with the body, whatever form it documents.
@pytest.mark.parametrize(
    "src, want",
    [
        (
            "(motif m ((real r 1))\n(doc 'A dot.')\n(circle c (r r)))\n",
            "(motif m ((real r 1))\n  doc@'A dot.'\n  (circle c (r r)))\n",
        ),
        (
            "(slider s v\n(from 0)\n(doc 'Sets v.'))\n",
            "(slider s v\n    (from 0)\n  doc@'Sets v.')\n",
        ),
        ("(real k 1 (doc 'It\\'s k.'))\n", "(real k 1 doc@'It\\'s k.')\n"),
        ("(text_ '(doc \\'x\\')') ; (doc 'y')\n", "(text_ '(doc \\'x\\')') ; (doc 'y')\n"),
    ],
)
def test_a_doc_is_written_doc_at_and_goes_2_in(src, want, tmp_path):
    assert layout(src) == want
    assert _emacs(want, tmp_path) == want


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


def test_the_keyword_tables_are_the_emacs_modes(tmp_path):
    if shutil.which("emacs") is None:
        pytest.skip("emacs is not installed")
    import subprocess

    code = (
        '(progn (dolist (e mtp-mode--keywords) (princ (string-join e " ")) (terpri))'
        ' (princ "no-body ") (princ (string-join mtp-mode--no-body " ")) (terpri))'
    )
    out = subprocess.run(
        ["emacs", "--batch", "-L", str(ROOT / "editors"), "-l", "mtp-mode.el", "--eval", code],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    lines = [line.split() for line in out.strip().split("\n")]
    assert {words[0]: set(words[1:]) for words in lines[:-1]} == KEYWORDS
    assert lines[-1][0] == "no-body"
    assert set(lines[-1][1:]) == NO_BODY


def test_a_tex_string_is_read_as_a_string():
    # Its parentheses and brackets are LaTeX, and a \\ before its closing quote does not escape it.
    src = "(scene s\n(text t tex'\\left( a \\\\'\n(fill red)))\n"
    assert layout(src) == "(scene s\n  (text t tex'\\left( a \\\\'\n      (fill red)))\n"
