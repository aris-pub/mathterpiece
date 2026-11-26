"""What the conformance tests of docs/spec/evaluation.md share: imports, sources and helpers."""

from fractions import Fraction

import pytest

from ..support import accepted, compile_error, in_folder, is_bound, mtpc, obj, same_meaning, value

RAND = "(import rand rand rand-int pick shuffle next-seed roll-dice) "

rule = pytest.mark.rule


def xfail(bead: str, why: str):
    return pytest.mark.xfail(strict=True, reason=f"{bead}: {why}")


FOLDED_NONE = xfail("mtp-ydd4.7.48", "min, max, range and xs[i] reject a folded call")

PICK = xfail("mtp-ydd4.7.49", "pick always has a type that includes none")

NONE_ARGUMENT = xfail("mtp-ydd4.7.50", "a call folds its body with an argument that is none")

REVERSE = xfail("mtp-ydd4.7.51", "reverse of a known list that holds none raises TypeError")

NONE_COLLECTION = xfail("mtp-ydd4.7.52", "a collection that may be none is rejected")

WHOLE_FORMS = xfail("mtp-08wd.2", "cond, and and or are compiled whole")

COPIES = xfail("mtp-08wd.1", "each copy of a foreach is proved with the value of its variable")

RAND_BOUNDS = xfail("mtp-y7vp", "rand and rand-int do not check that lo is at most hi")

ROUND = xfail("mtp-6yga", "round of 10^28 or more raises decimal.InvalidOperation")

MIX = xfail("mtp-nk2w", "the compiler rounds the channels of a mixed color halves to even")

SEED_SIGN = xfail("mtp-ydd4.7.30", "the type rand-seed is an int of at least 0")

SITES = xfail("mtp-ydd4.7.39", "the compiler counts the sites in the order in which it compiles")

EQUAL_FUNCTIONS = xfail("mtp-08wd.4", "the compiler accepts = and != with every type")

DEPTH = xfail("mtp-ydd4.7.15", "a call is folded only to a depth of about 80")

ROUNDED = xfail("mtp-ydd4.7.38", "the functions on reals are not correctly rounded")

# f gives none at 0, and its body is proved once, for every real x.
INVERSE = "(func f ((real x)) (/ 1 x))\n"

GIVES_NONE = [
    ("(/ 1 x)", "real", "0"),
    ("(mod 1 x)", "real", "0"),
    ("(^ x -1)", "real", "0"),
    ("(^ x 0.5)", "real", "-2"),
    ("(sqrt x)", "real", "-1"),
    ("(log x)", "real", "0"),
    ("(log x 2)", "real", "-1"),
    ("(log 2 x)", "real", "1"),
    ("(log 2 x)", "real", "0"),
    ("(tand x)", "real", "90"),
    ("(tand x)", "real", "-270"),
    ("(secd x)", "real", "90"),
    ("(cscd x)", "real", "180"),
    ("(cotd x)", "real", "0"),
    ("(csc x)", "real", "0"),
    ("(cot x)", "real", "0"),
    ("(asin x)", "real", "1.5"),
    ("(acos x)", "real", "-2"),
    ("(asind x)", "real", "2"),
    ("(acosd x)", "real", "2"),
    ("(asec x)", "real", "0.5"),
    ("(acsc x)", "real", "0"),
    ("(asecd x)", "real", "-0.5"),
    ("(acscd x)", "real", "0.9"),
    ("(to-polar [x 0])", "real", "0"),
    ("(range 0 1 (gap x))", "real", "0"),
    ("(range 0 1 (num x))", "int", "-1"),
]

GIVES_NONE_FOLD_REJECTS = [
    ("(min x)", "list[real]", "(as list[real] {})"),
    ("(max x)", "list[real]", "(as list[real] {})"),
    ("(range 0 x (gap 1))", "int", "2000000"),
    ("(. {1 2 3} x)", "int", "3"),
    ("(. {1 2 3} x)", "int", "-4"),
]


def _sites(d: dict) -> dict:
    """The site of each random variable of a .mtpc, by name."""
    found = {}
    for o in d["objects"]:
        bound = o.get("value", {}).get("bound")
        if bound and bound[0] in ("rand", "rand-int", "pick", "shuffle"):
            found[o["name"]] = bound[2]
    return found


__all__ = [
    "Fraction",
    "pytest",
    "accepted",
    "compile_error",
    "in_folder",
    "is_bound",
    "mtpc",
    "obj",
    "same_meaning",
    "value",
    "RAND",
    "rule",
    "xfail",
    "FOLDED_NONE",
    "PICK",
    "NONE_ARGUMENT",
    "REVERSE",
    "NONE_COLLECTION",
    "WHOLE_FORMS",
    "COPIES",
    "RAND_BOUNDS",
    "ROUND",
    "MIX",
    "SEED_SIGN",
    "SITES",
    "EQUAL_FUNCTIONS",
    "DEPTH",
    "ROUNDED",
    "INVERSE",
    "GIVES_NONE",
    "GIVES_NONE_FOLD_REJECTS",
    "_sites",
]
