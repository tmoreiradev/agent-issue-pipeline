"""Deterministic stand-in for the coding agent, so the demo and CI run without any API.

It reads the worker prompt (argv[1]), finds the issue id and plays a scripted behaviour:
  DEMO-1  implements the feature correctly on the first round;
  DEMO-3  reports the spec as impossible (`BLOCKED:`) and changes nothing;
  DEMO-4  ships a bug on round 1, then fixes it when the rejected review comes back as feedback.
"""

import re
import subprocess
import sys
from pathlib import Path

prompt = sys.argv[1]
iid = re.search(r"Implement issue (\S+)", prompt).group(1)
retry = "# Previous round rejected" in prompt


def write(path: str, text: str, mode: str = "a") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, mode, encoding="utf-8") as f:
        f.write(text)


def commit(msg: str) -> None:
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", msg], check=True)


if iid == "DEMO-1":
    write("calc.py", "\n\ndef subtract(a, b):\n    return a - b\n")
    write("tests/test_subtract.py", "import unittest\nfrom calc import subtract\n\n\n"
          "class T(unittest.TestCase):\n    def test_subtract(self):\n        self.assertEqual(subtract(5, 3), 2)\n")
    commit(f"feat: subtract() ({iid})")
    print("Implemented subtract() with a test.")
elif iid == "DEMO-3":
    print("Nothing implemented.\nBLOCKED: live exchange rates need a network API that this project does not have")
elif iid == "DEMO-4":
    body = "a * b" if retry else "a + b"  # round 1 ships a bug on purpose
    src = Path("calc.py").read_text(encoding="utf-8")
    src = re.sub(r"\n\n\ndef multiply\(a, b\):\n    return .*\n", "", src)
    Path("calc.py").write_text(src + f"\n\ndef multiply(a, b):\n    return {body}\n", encoding="utf-8")
    write("tests/test_multiply.py", "import unittest\nfrom calc import multiply\n\n\n"
          "class T(unittest.TestCase):\n    def test_multiply(self):\n"
          "        self.assertEqual(multiply(2, 3), 6)\n", "w")
    commit(f"{'fix' if retry else 'feat'}: multiply() ({iid})")
    print("Implemented multiply().")
else:
    print(f"mock worker has no script for {iid}")
