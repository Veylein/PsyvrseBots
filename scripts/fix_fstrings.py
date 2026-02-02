import re
from pathlib import Path
p = Path(r"c:\Users\brodr\OneDrive\Documents\PsyvrseBots\Pax-Bot\main.py")
s = p.read_text(encoding="utf-8")
# Pattern to find string prefixes followed by a quote
pattern = re.compile(r"(?P<prefix>(?:[fFrR]|rf|rF|Rf|RF|Fr|fR|FR)+)(?P<quote>['\"]{1,3})(?P<body>.*?)(?P=quote)", re.DOTALL)

changes = 0

def repl(m):
    global changes
    prefix = m.group('prefix')
    quote = m.group('quote')
    body = m.group('body')
    # If body contains braces, do not change (likely uses interpolation)
    if '{' in body or '}' in body:
        return m.group(0)
    # Remove f/F from prefix but keep r/R if present
    new_prefix = ''.join(ch for ch in prefix if ch.lower() != 'f')
    changes += 1
    return f"{new_prefix}{quote}{body}{quote}"

new_s, n = pattern.subn(repl, s)
# Actually count only replacements where prefix contained 'f' and body had no braces
# Write back
if n > 0:
    p.write_text(new_s, encoding="utf-8")
print(f"Processed {n} string literals; updated file: {p}")
