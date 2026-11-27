"""The schema itself (docs/spec/mtpc.schema.json): valid, and it accepts what docs/mtpc.md allows."""

from jsonschema import Draft202012Validator
from mtpc_check import SCHEMA, errors

from mathterpiece.mtpc import SPEC_VERSION

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
    return {
        "mtpc": SPEC_VERSION,
        "types": [],
        "objects": list(objects),
        "functions": [],
        "names": {},
    }


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


def variable(value):
    return {
        "kind": "variable",
        "type": "real",
        "access": "scene",
        "name": "k",
        "value": value,
        "token": False,
    }


def test_it_still_rejects_what_is_wrong():
    # The schema checks each expression, object and step only against the form its operation or
    # kind names; this checks that anything else is still caught.
    good = {"type": "real", "bound": ["lit", "real", 1], "deps": []}
    assert errors(doc(variable(good))) == []
    assert errors(doc(variable({**good, "bound": ["nope", "real", 1]}))) != []
    assert errors(doc(variable({**good, "bound": ["lit", "real"]}))) != []
    assert errors(doc(variable({**good, "bound": ["read", "real", "x", None, None]}))) != []
    assert errors(doc({**variable(good), "kind": "nope"})) != []
    assert errors(doc({**variable(good), "token": "yes"})) != []


def test_an_attribute_with_a_docstring():
    # A variable in a motif's body becomes an attribute of each instance, with its docstring.
    for value in (
        {"type": "real", "free": 1},
        {"type": "real", "bound": ["lit", "real", 1], "deps": []},
        {"type": "real", "start": ["lit", "real", 1], "deps": []},
    ):
        assert errors(doc(variable({**value, "doc": "d"}))) == []
        assert errors(doc(variable({**value, "doc": 1}))) != []


def control(kind, **keys):
    return {
        "kind": kind,
        "type": {"component": kind},
        "access": "page",
        "name": "c",
        "conditions": [],
        "active": None,
        **keys,
    }


def test_the_jumpers_of_the_controls_page():
    # The compiler cannot write these yet: docs/mtpc.md gives their form, and the runtime's tests
    # load them written by hand.
    real = {"type": "real", "free": 0}
    nothing = {"type": {"union": ["real", "none"]}, "free": None}
    yes = {"type": "bool", "free": True}
    label = {"label": {"type": "string", "free": ""}}
    track = {**label, "from": real, "to": real, "step": nothing, "ticks": nothing}
    option = {
        "value": {"type": "string", "free": "a"},
        "label": {"type": "string", "free": "x"},
        "label-tex": True,
    }
    k = variable({"type": "real", "free": 0})
    for c in (
        control("slider", target=[0, None], attrs=track),
        control("range-slider", low=[0, None], high=[0, None], attrs=track),
        control("dial", target=[0, None], attrs={**label, "step": nothing, "ticks": nothing}),
        control(
            "number-field",
            target=[0, None],
            attrs={**label, "step": real, "buttons": yes, "typing": yes},
        ),
        control("text-field", target=[0, None], attrs=label),
        control("select", target=[0, None], attrs=label, options=[option], **{"as": "radio"}),
        control(
            "multi-select", target=[0, None], attrs=label, options=[option], **{"as": "checkbox"}
        ),
    ):
        assert errors(doc(k, c)) == [], c["kind"]
    assert errors(doc(k, control("slider", target=[0, None], attrs=label))) != []
    wrong = control("select", target=[0, None], attrs=label, options=[option], **{"as": "checkbox"})
    assert errors(doc(k, wrong)) != []
    empty = control("select", target=[0, None], attrs=label, options=[], **{"as": "menu"})
    assert errors(doc(k, empty)) != []
