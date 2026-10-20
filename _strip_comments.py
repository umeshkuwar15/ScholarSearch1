import ast
import io
import os
import re
import tokenize

ROOT = r"d:/ScholarSearch1"

PY_FILES = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".pytest_cache", ".git", "node_modules", "venv", ".venv")]
    for fn in filenames:
        if fn.endswith(".py") and fn != "_strip_comments.py":
            PY_FILES.append(os.path.join(dirpath, fn))


def find_docstring_lines(src):
    lines = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return lines
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                for ln in range(first.lineno, getattr(first, "end_lineno", first.lineno) + 1):
                    lines.add(ln)
    return lines


for path in PY_FILES:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except Exception as e:
        print(f"SKIP (tokenize error): {path}: {e}")
        continue

    all_lines = src.split("\n")
    remove_lines = find_docstring_lines(src)
    inline_cuts = {}

    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            if row == 1 and col == 0 and all_lines and all_lines[0].lstrip().startswith("#!"):
                continue
            if row - 1 < len(all_lines) and all_lines[row - 1][:col].strip() == "":
                remove_lines.add(row)
            else:
                inline_cuts[row] = col

    new_lines = []
    for idx, line in enumerate(all_lines, start=1):
        if idx in remove_lines:
            continue
        if idx in inline_cuts:
            line = line[: inline_cuts[idx]].rstrip()
        new_lines.append(line)

    result = "\n".join(new_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = result.rstrip("\n") + "\n" if result.strip() else result

    if result != src:
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"MODIFIED: {path}")
    else:
        print(f"UNCHANGED: {path}")

