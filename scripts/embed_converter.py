import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COGS_DIR = ROOT / "Ludus-Bot" / "cogs"
OUT_FILE = ROOT / "embed_conversion_suggestions.json"

# conservative regex to find discord.Embed(...) blocks (may be multi-line)
EMBED_RE = re.compile(r"discord\.Embed\((.*?)\)", re.DOTALL)

suggestions = []

for dirpath, _, filenames in os.walk(COGS_DIR):
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        path = Path(dirpath) / fn
        text = path.read_text(encoding='utf-8', errors='ignore')
        for m in EMBED_RE.finditer(text):
            start = m.start()
            # line number (1-based)
            line_no = text.count('\n', 0, start) + 1
            original = m.group(0)

            # heuristic extraction for common args
            title_m = re.search(r"title\s*=\s*([rR]?['\"]{1,3}.*?['\"]{1,3})", original, re.DOTALL)
            desc_m = re.search(r"description\s*=\s*([rR]?['\"]{1,3}.*?['\"]{1,3})", original, re.DOTALL)
            color_m = re.search(r"color\s*=\s*([^,\)]+)", original)

            title = title_m.group(1) if title_m else None
            description = desc_m.group(1) if desc_m else None
            color = color_m.group(1).strip() if color_m else None

            # build a conservative suggested replacement (placeholder fields preserved)
            suggested_lines = ["# Suggested (manual review required):"]
            suggested_lines.append("from utils.embed_styles import EmbedBuilder, Colors")
            if title or description or color:
                call_args = []
                if title:
                    call_args.append(f"title={title}")
                if description:
                    call_args.append(f"description={description}")
                if color:
                    # map discord.Color.* to Colors.* conservatively by leaving color expression
                    call_args.append(f"color={color}")
                suggested_lines.append(f"embed = EmbedBuilder.create({', '.join(call_args)})")
            else:
                suggested_lines.append("# Complex embed detected; consider rewriting to EmbedBuilder.create(...) or EmbedBuilder.success(...) as appropriate")

            suggestion = {
                "file": str(path.relative_to(ROOT)),
                "line": line_no,
                "original_snippet": original.strip(),
                "suggested_snippet": "\n".join(suggested_lines)
            }
            suggestions.append(suggestion)

# write suggestions to JSON
OUT_FILE.write_text(json.dumps({"count": len(suggestions), "suggestions": suggestions}, indent=2), encoding='utf-8')
print(f"Found {len(suggestions)} discord.Embed occurrences. Suggestions written to: {OUT_FILE}")
