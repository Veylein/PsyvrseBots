import json
from pathlib import Path
try:
    from jsonschema import validate, ValidationError
except Exception:  # pragma: no cover - runtime environment may be missing dependency
    raise RuntimeError("Missing dependency 'jsonschema'. Add `jsonschema` to Conditor-Bot/requirements.txt and reinstall dependencies.")


def _validate_against_schema(data: dict, schema_p: Path):
    if not schema_p.exists():
        return
    with schema_p.open("r", encoding="utf-8") as sf:
        schema = json.load(sf)
    try:
        validate(instance=data, schema=schema)
    except ValidationError as ve:
        raise RuntimeError(f"Template validation failed: {ve.message}")


def load_template(name: str) -> dict:
    base = Path(__file__).parent
    p = base / f"{name}.json"
    schema_p = base / "schema.json"
    if not p.exists():
        raise FileNotFoundError(f"Template '{name}' not found at {p}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # normalize common keys: schema expects 'template_name'
    if "template_name" not in data and "name" in data:
        data["template_name"] = data["name"]

    # normalize roles: schema expects an object mapping template_name -> meta
    if isinstance(data.get('roles'), list):
        roles_obj = {}
        for i, item in enumerate(data.get('roles', [])):
            key = item.get('template_name') or item.get('name') or f'role_{i}'
            # copy allowed metadata fields
            meta = {k: v for k, v in item.items() if k not in ('template_name', 'name')}
            roles_obj[key] = meta
        data['roles'] = roles_obj

    _validate_against_schema(data, schema_p)
    return data


def load_default_template():
    return load_template("bot_testing")
