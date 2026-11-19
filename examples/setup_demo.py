"""Build a self-contained demo workspace: a bare "remote", a clone of a tiny project, four issues and a
pipeline.toml wired to the mock worker/reviewer and to a fake service with health check and rollback.

    python3 examples/setup_demo.py /tmp/demo
    python3 pipeline.py --config /tmp/demo/pipeline.toml --all
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

ISSUES = {
    "DEMO-1": ("Add subtract()", "task, ready-for-agent", """
`calc.py` needs a `subtract(a, b)` function.

## Acceptance criteria
- `subtract(5, 3) == 2`

## Evals
- A unit test covers it and the suite passes.
"""),
    "DEMO-2": ("Make it faster", "task, ready-for-agent", """
The calculator feels slow, please improve it.
"""),
    "DEMO-3": ("Convert with live exchange rates", "task, ready-for-agent", """
Add `convert(amount, currency)` using today's exchange rate.

## Acceptance criteria
- Uses the live rate from the central bank API.

## Evals
- Matches the published rate to 4 decimal places.
"""),
    "DEMO-4": ("Add multiply()", "task, ready-for-agent", """
`calc.py` needs a `multiply(a, b)` function.

## Acceptance criteria
- `multiply(2, 3) == 6`

## Evals
- A unit test covers it and the suite passes.
"""),
}

CONFIG = """# Demo configuration: mock agents, fake service. See pipeline.example.toml for real agents.
issues = "issues"
reports = "reports"
work = ".pipeline"
max_rounds = 3

[repo]
path = "project"
branch = "main"
checks = ["python3 -m unittest discover -s tests -q 2>&1 | tail -5"]

[worker]
command = ["{python}", "{base}/mock_worker.py", "{prompt}"]

[reviewer]
command = ["{python}", "{base}/mock_reviewer.py"]
command_name = "mock reviewer"

[deploy]
snapshot = "mkdir -p ../service && cp -f ../service/calc.py ../service/calc.prev 2>/dev/null || true"
build = "python3 -m py_compile calc.py"
up = "cp calc.py ../service/calc.py"
health = "cd ../service && python3 -c 'import calc; assert calc.add(2, 2) == 4'"
rollback = "cp -f ../service/calc.prev ../service/calc.py"
health_tries = 3
health_interval_seconds = 0.2
"""


def git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def main(ws: Path) -> None:
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    git("init", "-q", "--bare", "-b", "main", str(ws / "origin.git"))
    git("clone", "-q", str(ws / "origin.git"), str(ws / "project"))
    proj = ws / "project"
    for k, v in (("user.name", "demo"), ("user.email", "demo@example.com")):
        git("config", k, v, cwd=proj)
    (proj / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (proj / "tests").mkdir()
    (proj / "tests/test_add.py").write_text(
        "import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(2, 2), 4)\n")
    (proj / ".gitignore").write_text("__pycache__/\n")
    git("add", "-A", cwd=proj)
    git("commit", "-q", "-m", "chore: initial calculator", cwd=proj)
    git("push", "-q", "-u", "origin", "main", cwd=proj)
    (ws / "issues").mkdir()
    for iid, (title, labels, body) in ISSUES.items():
        (ws / "issues" / f"{iid}.md").write_text(
            f"---\nid: {iid}\ntitle: {title}\nstate: Todo\nlabels: [{labels}]\n---\n{body.lstrip()}")
    for name in ("mock_worker.py", "mock_reviewer.py"):
        shutil.copy(HERE / name, ws / name)
    (ws / "pipeline.toml").write_text(CONFIG)
    print(f"demo ready in {ws}\nrun: python3 pipeline.py --config {ws / 'pipeline.toml'} --all")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "demo").resolve())
