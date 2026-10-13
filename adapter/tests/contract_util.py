"""JSON Schema validation helpers for contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

SCHEMA_DIR = Path(__file__).resolve().parent / "contract" / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


def validate(instance: object, schema_name: str) -> None:
    jsonschema.validate(instance=instance, schema=load_schema(schema_name))
