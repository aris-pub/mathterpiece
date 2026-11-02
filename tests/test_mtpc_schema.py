"""The schema itself (docs/mtpc.schema.json): valid, and it accepts what docs/mtpc.md allows."""

from jsonschema import Draft202012Validator
from mtpc_check import SCHEMA, errors

TRANSITION = {
    "kind": "transition",
    "type": "transition",
    "access": "scene",
    "name": None,
    "from": None,
    "to": {"type": "real", "free": 1},
    "duration": None,
    "ease": None,
    "path": None,
}


def doc(*objects):
    return {"mtpc": 2, "types": [], "objects": list(objects), "functions": [], "names": {}}


def test_the_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


def test_a_transition_with_no_duration_or_ease_of_its_own():
    # Its moves carry the duration and ease resolved from the defaults around them.
    assert errors(doc(TRANSITION)) == []


def test_step_ease():
    assert errors(doc({**TRANSITION, "ease": ["step-ease", 0.5]})) == []
    assert errors(doc({**TRANSITION, "ease": ["step-ease", 2]})) != []


def test_a_font_value():
    font = {"family": None, "style": "normal", "weight": 400, "size": 16}
    variable = {
        "kind": "variable",
        "type": "font",
        "access": "scene",
        "name": "f",
        "value": {"type": "font", "free": font},
        "token": True,
    }
    assert errors(doc(variable)) == []
