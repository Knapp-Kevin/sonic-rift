"""How closely Sonic Rift's code resembles the original Chatterbox-TTS-UI it was forked from.

Two offline checks against the upstream commit in this repository's history:

- functions: for every non-trivial upstream function, the most similar function in Sonic Rift
  (difflib ratio over tokens, comments and docstrings ignored);
- lines: upstream Python lines of 30 or more characters that appear verbatim in Sonic Rift.

Read-only; tests are excluded. Similarity is evidence for review, not a legal conclusion.

    python scripts/audit_upstream_similarity.py [--ref HEAD] [--show 0.6]
"""

import argparse
import ast
import difflib
import io
import json
import subprocess
import sys
import textwrap
import tokenize
from pathlib import Path

UPSTREAM = "22460fd99ceb78c309f879b93878240241a0dc9b"
ROOT = Path(__file__).resolve().parents[1]
MIN_TOKENS = 12          # shorter upstream functions are one-liners, not evidence
MIN_LINE = 30


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=True).stdout.decode(
        "utf-8", "replace")


def python_files(ref, skip_tests):
    for path in git("ls-tree", "-r", "--name-only", ref).split("\n"):
        if path.endswith(".py") and not (skip_tests and path.startswith("tests/")):
            yield path, git("show", f"{ref}:{path}")


def tokens(source):
    try:
        found = [t.string for t in tokenize.generate_tokens(io.StringIO(source).readline)
                 if t.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)]
    except (tokenize.TokenError, IndentationError):
        found = source.split()
    return found


def functions(path, source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
            body = body[1:]                                   # the docstring
        if body:
            words = tokens(textwrap.dedent("\n".join(lines[body[0].lineno - 1:node.end_lineno])))
            yield f"{path}:{node.lineno} {node.name}", words


def function_matches(ref):
    ours = [(name, words, set(words)) for path, src in python_files(ref, True) for name, words in functions(path, src)]
    rows = []
    for path, src in python_files(UPSTREAM, False):
        for name, words in functions(path, src):
            if len(words) < MIN_TOKENS:
                continue
            vocabulary, best = set(words), (0.0, None)
            for candidate, their_words, their_vocabulary in ours:
                overlap = len(vocabulary & their_vocabulary) / max(1, len(vocabulary | their_vocabulary))
                if overlap >= 0.25:
                    ratio = difflib.SequenceMatcher(None, words, their_words, autojunk=False).ratio()
                    best = max(best, (ratio, candidate), key=lambda pair: pair[0])
            rows.append({"upstream": name, "ratio": round(best[0], 3), "closest": best[1]})
    return sorted(rows, key=lambda row: -row["ratio"])


def shared_lines(ref):
    upstream = {line.strip() for _path, src in python_files(UPSTREAM, False) for line in src.splitlines()
                if len(line.strip()) >= MIN_LINE and not line.strip().startswith(("import ", "from ", "#"))}
    return [{"path": path, "line": number, "text": line.strip()}
            for path, src in python_files(ref, True)
            for number, line in enumerate(src.splitlines(), 1) if line.strip() in upstream]


def audit(ref="HEAD"):
    return {"upstream": UPSTREAM, "ref": ref, "functions": function_matches(ref), "lines": shared_lines(ref)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--show", type=float, default=0.6, help="list upstream functions at or above this ratio")
    parser.add_argument("--json", help="also write the full result here")
    options = parser.parse_args(argv)
    result = audit(options.ref)
    if options.json:
        Path(options.json).write_text(json.dumps(result, indent=1), encoding="utf-8")
    ratios = [row["ratio"] for row in result["functions"]]
    print(f"{len(ratios)} upstream functions; highest similarity {max(ratios):.2f}; "
          f"{sum(r >= 0.8 for r in ratios)} at 0.8 or above; {len(result['lines'])} shared lines")
    for row in result["functions"]:
        if row["ratio"] >= options.show:
            print(f"  {row['ratio']:.2f}  {row['upstream']}  ->  {row['closest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
