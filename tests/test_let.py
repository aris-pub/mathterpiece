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


# A let whose body holds declarations (mtp-gvrf.2).

_DOTS = (
    "(real m 1 (>= 0)) (func[list[point]] dots-of ((real s)) (map 5 (fn k [(* k s) 0])))"
    " (scene sc (let ((pts (dots-of m)))"
    " (polyline_ (points pts)) (foreach k 5 (circle_ (pos (or? pts[k] [0 0])) (r 1)))))"
)


def _in(d, op):
    """The written expressions anywhere among the objects whose op is op."""

    def walk(x):
        if isinstance(x, dict):
            return [e for v in x.values() for e in walk(v)]
        if isinstance(x, list) and x and isinstance(x[0], str):
            return _ops(x, op)
        if isinstance(x, list):
            return [e for v in x for e in walk(v)]
        return []

    return walk(d["objects"])


def _calls(d):
    return _in(d, "call")


def _held(d):
    """The variables the compiler makes to hold a let's values."""
    return [o for o in d["objects"] if o["kind"] == "variable" and "let" in o]


def test_a_value_read_by_many_shapes_is_worked_out_once():
    d = doc(_DOTS)
    assert len(_calls(d)) == 1
    (held,) = _held(d)
    assert held["let"] == "pts" and held["name"] is None
    assert held["value"]["bound"][0] == "call"


def test_each_shape_reads_the_held_value():
    d = doc(_DOTS)
    (i,) = [i for i, o in enumerate(d["objects"]) if "let" in o]
    reads = [e for e in _in(d, "read") if e[2] == i]
    # The polyline's points, and each circle's x and y.
    assert len(reads) == 11


def test_each_foreach_copy_holds_its_own_value():
    d = doc(
        "(real m 1 (>= 0))"
        " (scene sc (foreach i 3 (let ((v (* m (+ i 1)))) (circle_ (r v)) (circle_ (x v) (r 1)))))"
    )
    assert len(_held(d)) == 3
    assert len([e for e in _in(d, "builtin") if e[2] == "*"]) == 3


def test_each_motif_instance_holds_its_own_value():
    d = doc(
        "(motif dots ((real s 1 (>= 0))) (let ((v (* s 2))) (circle_ (r v)) (circle_ (x v) (r 1))))"
        " (real m 1 (>= 0)) (scene sc (dots a (s m)) (dots b (s (+ m 1))))"
    )
    assert len(_held(d)) == 2


def test_a_known_value_in_a_body_is_folded_as_before():
    d = doc("(scene sc (let ((v (* 2 3))) (circle_ (r v))))")
    assert _held(d) == []


def test_a_shape_in_a_body_stays_written_out():
    d = doc(
        "(int i 0 (>= 0) (<= 1))"
        " (scene sc (circle a (r 1)) (circle b (r 2)) (let ((c [a b][i])) (circle_ (r c.r))))"
    )
    assert _held(d) == []


# A let among a group's members reads in the group's frame, as its members do (mtp-gvrf.4).


def _frames(d, name):
    """The frames of the reads in what shape name's x is bound to, through any held value."""
    objects = d["objects"]
    (o,) = [o for o in objects if o["name"] == name]
    found = []
    for e in _ops(o["attrs"]["x"]["bound"], "read"):
        held = objects[e[2]]
        if held["kind"] == "variable" and "let" in held:
            found += [r[4] for r in _ops(held["value"]["bound"], "read")]
        else:
            found.append(e[4])
    return set(found)


def _index(d, name):
    (i,) = [i for i, o in enumerate(d["objects"]) if o["name"] == name]
    return i


def test_a_let_in_a_group_reads_in_the_groups_frame():
    d = doc(
        "(real m 1) (scene sc (group g (translate [5 0]) (circle a (x m) (r 1))"
        " (let ((p a.pos)) (circle b (pos p) (r 1))) (circle c (pos a.pos) (r 1))))"
    )
    assert _frames(d, "c") == {_index(d, "g")}
    assert _frames(d, "b") == {_index(d, "g")}


def test_a_let_in_a_nested_group_reads_in_the_inner_groups_frame():
    d = doc(
        "(real m 1) (scene sc (group g (translate [5 0]) (group h (transform (rotate 90))"
        " (circle a (x m) (r 1)) (let ((p a.pos)) (circle b (pos p) (r 1))))))"
    )
    assert _frames(d, "b") == {_index(d, "h")}


def test_a_let_in_a_foreach_in_a_group_reads_in_the_groups_frame():
    d = doc(
        "(real m 1) (scene sc (group g (translate [5 0]) (circle a (x m) (r 1))"
        " (foreach i 2 (let ((p a.pos)) (circle #'b{i}' (pos p) (r 1))))))"
    )
    assert _frames(d, "b0") == {_index(d, "g")}


def test_a_foreach_in_a_group_reads_its_list_in_the_groups_frame():
    d = doc(
        "(real m 1) (scene sc (group g (translate [5 0]) (circle a (x m) (r 1))"
        " (foreach q [a.pos] (circle b (pos q) (r 1)))))"
    )
    assert _frames(d, "b") == {_index(d, "g")}


def test_an_exists_when_in_a_group_reads_in_the_groups_frame():
    d = doc(
        "(real m 1) (scene sc (group g (translate [5 0]) (circle a (x m) (r 1))"
        " (circle|none b (r 1)) (exists-when b (< a.x 3))))"
    )
    (o,) = [o for o in d["objects"] if o["name"] == "b"]
    assert {e[4] for e in _ops(o["attrs"]["exists"]["bound"], "read")} == {_index(d, "g")}


def test_a_let_in_the_scene_reads_a_group_member_in_the_scenes_frame():
    d = doc(
        "(real m 1) (scene sc (group g (translate [5 0]) (circle a (x m) (r 1)))"
        " (let ((p a.pos)) (circle b (pos p) (r 1))) (circle c (pos a.pos) (r 1)))"
    )
    assert _frames(d, "c") == {None}
    assert _frames(d, "b") == {None}


def test_a_let_in_a_motif_reads_in_the_instances_frame():
    d = doc(
        "(real m 1) (motif one () (circle a (x m) (r 1))"
        " (let ((p a.pos)) (circle b (pos p) (r 1))))"
        " (scene sc (one o (translate [5 0])))"
    )
    assert _frames(d, "b") == {_index(d, "o")}
