import json
from pathlib import Path
from conditor.templates.loader import load_template
from conditor.parser import TemplateParser


def main():
    print("Conditor dry-run: listing available templates")
    tpl_dir = Path(__file__).resolve().parents[1] / "src" / "conditor" / "templates"
    for f in tpl_dir.glob("*.json"):
        if f.name == "schema.json":
            continue
        print(f" - {f.name}")

    # pick the two new templates and show deterministic plans for a fake actor
    actor_id = 123456789012345678
    examples = ["community_builder", "game_server"]
    for name in examples:
        tpl = load_template(name)
        parser = TemplateParser(tpl)
        plan = parser.generate(inputs={"project_name": name}, actor_id=actor_id)
        print(f"\nPlan for template '{name}':\n")
        print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
