import ast
from pathlib import Path
import sys

p = Path(r"c:\Users\brodr\OneDrive\Documents\PsyvrseBots\Pax-Bot\main.py")
src = p.read_text(encoding='utf-8')
try:
    tree = ast.parse(src)
except SyntaxError as e:
    print('Syntax error parsing file:', e)
    sys.exit(1)

# collect ranges to replace: (start_offset, end_offset, replacement)
repls = []
lines = src.splitlines(keepends=True)

def pos_to_offset(lineno, col):
    # lineno is 1-based
    return sum(len(lines[i]) for i in range(lineno-1)) + col

for node in ast.walk(tree):
    if isinstance(node, ast.JoinedStr):
        # JoinedStr is f-string; check if it contains any FormattedValue
        has_formatted = any(isinstance(v, ast.FormattedValue) for v in node.values)
        if not has_formatted:
            # extract literal text by concatenating Constant/Str values
            parts = []
            ok = True
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
                elif isinstance(v, ast.Str):
                    parts.append(v.s)
                else:
                    ok = False
                    break
            if not ok:
                continue
            new_literal = repr(''.join(parts))
            # compute start/end offsets
            start = pos_to_offset(node.lineno, node.col_offset)
            # ast in py3.8+ has end_lineno/end_col_offset
            end = pos_to_offset(node.end_lineno, node.end_col_offset)
            orig = src[start:end]
            # only replace if original starts with f or F in prefix
            # find prefix by scanning backwards from start to include possible prefixes like fr, rf
            # but easier: check if orig starts with f or contains f before quote
            if orig.lstrip().startswith(('f"', "f'", "F\"", "F'", "fr\"", "fr'", "rf\"", "rf'", "Fr\"", "Fr'")):
                repl_text = new_literal
            else:
                # still, try to strip leading f or F in orig
                # find index of first quote in orig
                idx_quote = None
                for i,ch in enumerate(orig):
                    if ch in '"\'' and (i==0 or orig[i-1] != '\\'):
                        idx_quote = i
                        break
                if idx_quote is None:
                    continue
                # check prefix
                prefix = orig[:idx_quote]
                if 'f' in prefix.lower():
                    repl_text = new_literal
                else:
                    continue
            repls.append((start,end,repl_text,orig))

if not repls:
    print('No f-strings without placeholders found via AST.')
    sys.exit(0)

# apply replacements from end to start
repls.sort(key=lambda x: x[0], reverse=True)
new_src = src
for start,end,repl_text,orig in repls:
    new_src = new_src[:start] + repl_text + new_src[end:]

p.write_text(new_src, encoding='utf-8')
print(f'Applied {len(repls)} replacements to {p}')
