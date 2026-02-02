import tokenize
import io


def remove_f_prefix_from_file(path: str) -> None:
    with tokenize.open(path) as f:
        src = f.read()

    tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    changed = False
    new_tokens = []

    for toknum, tokval, start, end, line in tokens:
        if toknum == tokenize.STRING:
            sval = tokval
            # quick check for f/Fr/rf prefixes
            lower = sval[:3].lower()
            prefix_len = 0
            if lower.startswith(('fr', 'rf')):
                prefix_len = 2
            elif sval[:1].lower() == 'f':
                prefix_len = 1
            else:
                prefix_len = 0

            if prefix_len > 0:
                # If there are no braces, it's safe to drop the f-prefix
                if ('{' not in sval) and ('}' not in sval):
                    # remove only the f/r/fR/RF part, keep other prefixes (r, b) intact
                    # find the first quote char position
                    rest = sval[prefix_len:]
                    # keep case of remaining prefix (if any)
                    new_val = rest
                    if new_val != sval:
                        sval = new_val
                        changed = True
            new_tokens.append((toknum, sval))
        else:
            new_tokens.append((toknum, tokval))

    if not changed:
        print(f"No non-interpolated f-strings found in {path}.")
        return

    new_src = tokenize.untokenize(new_tokens)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_src)
    print(f"Cleaned non-interpolated f-strings in {path}.")


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python remove_non_interpolated_f_prefix.py path/to/file.py')
        sys.exit(1)
    remove_f_prefix_from_file(sys.argv[1])
