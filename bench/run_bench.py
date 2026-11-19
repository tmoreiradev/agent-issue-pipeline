#!/usr/bin/env python3
"""Benchmark: run the pipeline over 20 issues with known expected outcomes and score it.

    python bench/run_bench.py --mode review      # Claude Code worker + Codex reviewer (real agents)
    python bench/run_bench.py --mode no-review   # same worker, reviewer replaced by "approve if checks pass"
    python bench/run_bench.py --mode mock        # deterministic agents: tests the harness, measures nothing

Each run builds a fresh workspace: a bare `origin`, a clone of `bench/project` (a small Brazilian-documents
library), the 20 issues and a `pipeline.toml`. After `pipeline.py --all`, every issue is scored against
`expected.toml`; approved work is checked with hidden acceptance tests (`bench/hidden`) that the agents never
see, run against the final `main` of `origin`. Results go to `bench/results/<date>-<mode>.json` and
`bench/RESULTS.md` is regenerated from the latest result of each mode.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import tomllib
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent
sys.path.insert(0, str(ROOT))
from tracker import Tracker  # noqa: E402

REVIEW_PROMPT = "Read REVIEW.md in this folder and do exactly the review it describes."
CLAUDE = ["claude", "-p", "{prompt}", "--model", "{model}", "--output-format", "json",
          "--permission-mode", "bypassPermissions",
          "--disallowedTools", "Bash(docker:*)", "Bash(sudo:*)", "Bash(git push:*)"]
APPROVE = ["{python}", "-c", "print('No review in this mode.\\nVERDICT: APPROVED')"]

AGENTS = {
    "review": {
        "worker": {"command": CLAUDE, "model": "sonnet", "timeout_minutes": 20},
        "reviewer": {"command": ["codex", "exec", "-s", "read-only", "--skip-git-repo-check",
                                 "-c", "windows.sandbox=unelevated", "-o", "{out}", REVIEW_PROMPT],
                     "command_name": "codex",
                     "fallback": ["claude", "-p", REVIEW_PROMPT, "--model", "opus", "--output-format", "json"],
                     "fallback_name": "claude opus (fallback)", "timeout_minutes": 20},
    },
    "no-review": {
        "worker": {"command": CLAUDE, "model": "sonnet", "timeout_minutes": 20},
        "reviewer": {"command": APPROVE, "command_name": "none (checks only)"},
    },
    "mock": {
        "worker": {"command": ["{python}", str(BENCH / "mock_bench_worker.py"), "{prompt}"]},
        "reviewer": {"command": ["{python}", str(ROOT / "examples" / "mock_reviewer.py")],
                     "command_name": "mock reviewer"},
    },
}


def toml_value(v) -> str:
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    if isinstance(v, (int, float)):
        return str(v)
    return json.dumps(v)  # a JSON string is a valid TOML basic string


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def rm_tree(path: Path) -> None:
    """rmtree that also removes git's read-only object files on Windows."""
    def make_writable(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    if path.exists():
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=make_writable)
        else:
            shutil.rmtree(path, onerror=make_writable)


MARKER = ".bench-workspace"


def setup(ws: Path, mode: str) -> None:
    if ws.exists():
        # Only ever delete a folder this script created: `--workspace .` must not wipe a repository.
        if any(ws.iterdir()) and not (ws / MARKER).exists():
            sys.exit(f"{ws} exists and is not a benchmark workspace; pick an empty or new folder")
        rm_tree(ws)
    ws.mkdir(parents=True)
    (ws / MARKER).write_text("created by bench/run_bench.py\n")
    git("init", "-q", "--bare", "-b", "main", str(ws / "origin.git"))
    git("clone", "-q", str(ws / "origin.git"), str(ws / "project"))
    proj = ws / "project"
    for k, v in (("user.name", "bench"), ("user.email", "bench@example.com"), ("core.autocrlf", "false")):
        git("config", k, v, cwd=proj)
    shutil.copytree(BENCH / "project", proj, dirs_exist_ok=True)
    (proj / ".gitignore").write_text("__pycache__/\n")
    git("add", "-A", cwd=proj)
    git("commit", "-q", "-m", "chore: brdocs with CPF validation", cwd=proj)
    git("push", "-q", "-u", "origin", "main", cwd=proj)
    shutil.copytree(BENCH / "issues", ws / "issues")
    check = f'"{sys.executable}" -m unittest discover -s tests -q 2>&1 | tail -15'.replace("\\", "/")
    lines = ['issues = "issues"', 'reports = "reports"', 'work = ".pipeline"', "max_rounds = 3", "",
             "[repo]", 'path = "project"', 'branch = "main"', f"checks = [{json.dumps(check)}]"]
    for section, values in AGENTS[mode].items():
        lines += ["", f"[{section}]"] + [f"{k} = {toml_value(v)}" for k, v in values.items()]
    (ws / "pipeline.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


HIDDEN_TIMEOUT_S = 120


def hidden_test(iid: str) -> Path:
    return BENCH / "hidden" / f"test_{iid.lower().replace('-', '_')}.py"


def run_hidden(repo: Path, ref: str, test: Path, where: Path) -> tuple[bool, str]:
    """Fresh checkout of `ref` from `repo` into `where`, then run one hidden test file there.
    Returns (passed, commit). A hanging implementation counts as a failure, not as a stuck benchmark."""
    rm_tree(where)  # never score a stale checkout
    git("clone", "-q", str(repo), str(where))
    git("checkout", "-q", ref, cwd=where)
    sha = git("rev-parse", "--short", "HEAD", cwd=where).strip()
    shutil.copy(test, where / test.name)
    try:
        r = subprocess.run([sys.executable, "-m", "unittest", "-q", test.stem], cwd=where, capture_output=True,
                           text=True, timeout=HIDDEN_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return False, sha
    return r.returncode == 0, sha


def merged_head(ws: Path, iid: str, rep: dict) -> str | None:
    """The commit this issue pushed. Hidden tests run there, not on the final main, so a later issue can
    neither hide nor cause a failure in an earlier merge decision."""
    if rep.get("head"):
        return rep["head"]
    log = ws / "reports" / "pipeline-log.md"  # runs recorded before the `head` field existed
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            if f" {iid} " in line and (m := re.search(r"merged \(`([0-9a-f]+)`\)", line)):
                return m.group(1)
    return None


def branch_passes(ws: Path, iid: str) -> tuple[bool | None, str | None]:
    """For work the pipeline did not merge: would the hidden test have passed on the worker's branch?
    Tells a correct rejection from a false one."""
    branch = f"pipeline/{iid}"
    if subprocess.run(["git", "rev-parse", "--verify", "-q", branch], cwd=ws / "project",
                      capture_output=True).returncode:
        return None, None
    return run_hidden(ws / "project", branch, hidden_test(iid), ws / "checkouts" / iid)


def score(ws: Path, mode: str, minutes: float) -> dict:
    expected = {k.replace("_", "-"): v for k, v in tomllib.loads((BENCH / "expected.toml").read_text()).items()}
    tr = Tracker(ws / "issues")
    rows = []
    for iid, exp in expected.items():
        issue = tr.get(iid)
        rep_file = ws / "reports" / f"{iid}.json"
        rep = json.loads(rep_file.read_text()) if rep_file.exists() else {}
        if "needs-info" in issue["labels"]:
            actual = "gate"
        elif rep.get("merged"):
            actual = "merged"
        else:
            actual = rep.get("outcome", "not run")
        passed = sha = on_branch = None
        if exp["expect"] == "approve" and actual == "merged":
            head = merged_head(ws, iid, rep)
            passed, sha = (run_hidden(ws / "origin.git", head, hidden_test(iid), ws / "checkouts" / iid)
                           if head else (False, None))
        elif exp["expect"] == "approve":
            on_branch, sha = branch_passes(ws, iid)
        if exp["expect"] == "gate":
            correct = actual == "gate"
        elif exp["expect"] == "escalate":
            correct = actual in ("escalated", "rejected")  # handed to a human, nothing merged
        else:
            correct = actual == "merged" and bool(passed)
        rows.append({"id": iid, "category": exp["category"], "expect": exp["expect"], "actual": actual,
                     "hidden_tests": passed, "tested_commit": sha, "correct": correct,
                     "false_approval": actual == "merged" and (exp["expect"] != "approve" or passed is False),
                     "unmerged_branch_passes_hidden": on_branch, "false_rejection": on_branch is True,
                     **{k: rep.get(k) for k in ("rounds", "minutes", "cost_usd", "tokens", "agent_calls")}})
    agent_rows = [r for r in rows if r["rounds"]]
    merged = [r for r in rows if r["actual"] == "merged"]
    return {
        "mode": mode, "date": dt.date.today().isoformat(), "wall_minutes": round(minutes, 1), "issues": rows,
        "summary": {
            "correct": sum(r["correct"] for r in rows), "total": len(rows),
            "by_category": {c: f"{sum(r['correct'] for r in rows if r['category'] == c)}/"
                               f"{sum(1 for r in rows if r['category'] == c)}"
                            for c in ("feasible", "hard", "impossible", "gate")},
            "false_approvals": sum(r["false_approval"] for r in rows),
            "false_rejections": sum(r["false_rejection"] for r in rows),
            "merged": len(merged),
            "first_round_merges": sum(1 for r in merged if r["rounds"] == 1),
            "avg_rounds": round(sum(r["rounds"] for r in agent_rows) / len(agent_rows), 2) if agent_rows else 0,
            "agent_minutes": round(sum(r["minutes"] or 0 for r in agent_rows), 1),
            "cost_usd": round(sum(r["cost_usd"] or 0 for r in agent_rows), 2),
            "tokens": sum(r["tokens"] or 0 for r in agent_rows),
        },
    }


def write_results_md() -> None:
    runs = [json.loads(f.read_text()) for f in (BENCH / "results").glob("*.json")]
    runs = sorted((r for r in runs if r["mode"] != "mock"), key=lambda r: r.get("finished_at", ""))
    latest = {r["mode"]: r for r in runs}  # newest run of each mode
    if not latest:
        return
    modes = [m for m in ("review", "no-review") if m in latest]
    s = {m: latest[m]["summary"] for m in modes}
    head = "| | " + " | ".join(modes) + " |\n|---|" + "---|" * len(modes) + "\n"
    rows = [("Correct outcomes", lambda x: f"{x['correct']}/{x['total']}"),
            ("Feasible (merged + hidden tests pass)", lambda x: x["by_category"]["feasible"]),
            ("Hard (merged + hidden tests pass)", lambda x: x["by_category"]["hard"]),
            ("Impossible (handed to a human)", lambda x: x["by_category"]["impossible"]),
            ("Underspecified (stopped at the gate)", lambda x: x["by_category"]["gate"]),
            ("False approvals (merged, hidden test fails)", lambda x: x["false_approvals"]),
            ("False rejections (not merged, branch passes hidden test)", lambda x: x["false_rejections"]),
            ("Merged on the first round", lambda x: f"{x['first_round_merges']}/{x['merged']}"),
            ("Average rounds per issue", lambda x: x["avg_rounds"]),
            ("Agent time (min)", lambda x: x["agent_minutes"]),
            ("Tokens", lambda x: f"{x['tokens']:,}"),
            ("Cost reported by the Claude CLI (US$)", lambda x: f"{x['cost_usd']:.2f}")]
    table = head + "".join(f"| {name} | " + " | ".join(str(fn(s[m])) for m in modes) + " |\n" for name, fn in rows)
    detail = ""
    for m in modes:
        detail += (f"\n### {m}, {latest[m].get('tag') or 'untagged'} ({latest[m]['date']})\n\n"
                   "| Issue | Category | Expected | Actual | Hidden tests | Rounds | Min | US$ |\n"
                   "|---|---|---|---|---|---|---|---|\n")
        for r in latest[m]["issues"]:
            ht = "" if r["hidden_tests"] is None else ("pass" if r["hidden_tests"] else "FAIL")
            if r.get("unmerged_branch_passes_hidden") is not None:
                ht = "branch passes" if r["unmerged_branch_passes_hidden"] else "branch fails"
            cost = "" if r["cost_usd"] is None else f"{r['cost_usd']:.2f}"
            detail += (f"| {r['id']} | {r['category']} | {r['expect']} | {r['actual']} | {ht} | "
                       f"{r['rounds'] or ''} | {r['minutes'] or ''} | {cost} |\n")
    history = ("\n## All runs\n\n| Finished | Mode | Tag | Correct | False approvals | False rejections | US$ |\n"
               "|---|---|---|---|---|---|---|\n")
    for r in runs:
        x = r["summary"]
        history += (f"| {r.get('finished_at', r['date'])} | {r['mode']} | {r.get('tag') or ''} | "
                    f"{x['correct']}/{x['total']} | {x['false_approvals']} | {x.get('false_rejections', '')} | "
                    f"{x['cost_usd']:.2f} |\n")
    tags = ", ".join(f"{m}: {latest[m].get('tag') or 'untagged'}" for m in modes)
    (BENCH / "RESULTS.md").write_text("# Benchmark results\n\nGenerated by `bench/run_bench.py`; see the README "
                                      f"for the method and its limits.\n\nLatest run of each mode ({tags}).\n\n"
                                      + table + detail + history, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=sorted(AGENTS), required=True)
    ap.add_argument("--workspace", type=Path, help="where to build the run (default: bench/.work/<mode>)")
    ap.add_argument("--no-save", action="store_true", help="print the score, don't write bench/results")
    ap.add_argument("--score-only", action="store_true", help="re-score an existing workspace without running agents")
    ap.add_argument("--tag", default="", help="label for this run, kept in the result file name and history")
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._-]*", a.tag):  # it becomes part of a file name: check before spending agents
        sys.exit("--tag may only contain letters, digits, '.', '_' and '-'")
    ws = (a.workspace or BENCH / ".work" / a.mode).resolve()
    if not a.score_only:
        setup(ws, a.mode)
        started = time.monotonic()
        with open(ws / "pipeline.log", "w", encoding="utf-8") as logf:
            r = subprocess.run([sys.executable, str(ROOT / "pipeline.py"), "--config", str(ws / "pipeline.toml"),
                                "--all"], stdout=logf, stderr=subprocess.STDOUT)
        if r.returncode:
            sys.exit(f"pipeline exited {r.returncode}; see {ws / 'pipeline.log'}")
        (ws / "wall_minutes.txt").write_text(f"{(time.monotonic() - started) / 60:.2f}")
    wall = ws / "wall_minutes.txt"
    result = score(ws, a.mode, float(wall.read_text()) if wall.exists() else 0.0)
    result["tag"] = a.tag
    name = f"{result['date']}-{a.mode}" + (f"-{a.tag}" if a.tag else "")
    target = BENCH / "results" / f"{name}.json"
    now = dt.datetime.now().isoformat(timespec="seconds")
    if a.score_only and target.exists():  # a re-score keeps the run's own finish time, so it never looks newer
        old = json.loads(target.read_text())
        result.update({k: old[k] for k in ("date", "finished_at", "finished_at_note") if k in old})
        result["rescored_at"] = now
    else:
        result["finished_at"] = now
        if target.exists():  # a new run never overwrites an earlier one
            target = target.with_name(f"{name}-{now[11:].replace(':', '')}.json")
    print(json.dumps(result["summary"], indent=2))
    if not a.no_save:
        (BENCH / "results").mkdir(exist_ok=True)
        target.write_text(json.dumps(result, indent=2))
        write_results_md()


if __name__ == "__main__":
    main()
