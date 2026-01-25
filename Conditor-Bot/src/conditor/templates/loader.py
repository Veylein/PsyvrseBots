import json
from pathlib import Path
from jsonschema import validate, ValidationError


def load_default_template():
    base = Path(__file__).parent
    p = base / "bot_testing.json"
    schema_p = base / "schema.json"
    if not p.exists():
        raise FileNotFoundError("Default template not found")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # validate against schema if present
    if schema_p.exists():
        with schema_p.open("r", encoding="utf-8") as sf:
            schema = json.load(sf)
        try:
            validate(instance=data, schema=schema)
        except ValidationError as ve:
            # surface a helpful message
            raise RuntimeError(f"Template validation failed: {ve.message}")

    return data
