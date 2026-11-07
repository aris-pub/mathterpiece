"""A let's value is worked out once, however often its name is read (mtp-rjda)."""

import json

from helpers import doc, value


def _ops(e, op):
    """The sub-expressions of a written expression whose op is op."""
    if not isinstance(e, list):
        return []
    found = [e] if e and e[0] == op else []
    return found + [x for part in e for x in _ops(part, op)]


def _value_of(d, name):
    (o,) = [o for o in d["objects"] if o["name"] == name]
    return o["value"]["bound"]


def test_a_value_known_only_while_drawing_is_bound_once():
    d = doc("(real m 1) (real v (let ((s (* m 2))) (+ s s s s)))")
    (let,) = _ops(_value_of(d, "v"), "let")
    ((name, bound),) = let[2]
    assert bound[0] == "builtin" and bound[2] == "*"
    assert [e[2] for e in _ops(let[3], "local")] == [name] * 4


def test_a_known_value_is_folded_as_before():
    assert value("(real v (let ((s (* 2 3))) (+ s s)))") == 12


def test_a_shape_stays_written_out():
    d = doc(
        "(int i 0 (>= 0) (<= 1)) (scene sc (circle a (r 1)) (circle b (r 2)))"
        " (real v (let ((c [a b][i])) c.r))"
    )
    assert _ops(_value_of(d, "v"), "let") == []


def test_an_unused_name_is_dropped():
    d = doc("(real m 1) (real v (let ((s (* m 2))) m))")
    assert _ops(_value_of(d, "v"), "let") == []


def test_names_never_clash():
    d = doc("(real m 1) (real v (let ((a (* m 2))) (let ((b a) (a (+ m 1))) (+ b a))))")
    names = [e[2] for e in _ops(_value_of(d, "v"), "local")]
    assert len(set(names)) == 2, json.dumps(names)
