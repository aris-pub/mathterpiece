"""Checks an .mtpc document against docs/mtpc.schema.json."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = json.loads((Path(__file__).parent.parent / "docs" / "mtpc.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def errors(doc) -> list[str]:
    return [
        f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in VALIDATOR.iter_errors(doc)
    ]
