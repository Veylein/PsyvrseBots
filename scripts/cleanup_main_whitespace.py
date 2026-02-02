import re
from pathlib import Path
p = Path(r"c:\Users\brodr\OneDrive\Documents\PsyvrseBots\Pax-Bot\main.py")
s = p.read_text(encoding="utf-8")
# Remove trailing whitespace
s = "\n".join(line.rstrip() for line in s.splitlines()) + "\n"
# Collapse more than 2 consecutive blank lines into exactly 2
s = re.sub(r"\n{3,}", "\n\n", s)
# Ensure file ends with a single newline
s = s.rstrip('\n') + '\n'
p.write_text(s, encoding="utf-8")
print("Cleaned whitespace in main.py")
