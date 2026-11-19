"""Deterministic worker for `run_bench.py --mode mock`: it commits the reference solution (plus a smoke
test) for solvable issues and answers `BLOCKED:` for the impossible ones. It exists to test the benchmark
harness and the hidden tests in CI, not to measure anything."""

import re
import subprocess
import sys
from pathlib import Path

REF = Path(__file__).resolve().parent / "reference"
prompt = sys.argv[1]
iid = re.search(r"Implement issue (\S+)", prompt).group(1)
ref = REF / f"{iid}.py"

if ref.exists():
    lines = ref.read_text(encoding="utf-8").splitlines(keepends=True)
    module = lines[0].removeprefix("# module: ").strip()
    Path(module).write_text("".join(lines[1:]), encoding="utf-8")
    name = Path(module).stem
    Path(f"tests/test_{name}.py").write_text(
        f"import unittest\n\nimport brdocs.{name}  # noqa: F401\n\n\nclass Smoke(unittest.TestCase):\n"
        "    def test_import(self):\n        self.assertTrue(True)\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"feat: {name} ({iid})"], check=True)
    print(f"Implemented {module}.")
else:
    print("Nothing implemented.\nBLOCKED: needs live network data, which the project rules forbid")
