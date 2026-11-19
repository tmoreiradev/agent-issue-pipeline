"""Unit tests for the pure parts plus an end-to-end run of the demo with the mock agents.

Run with `python3 -m pytest -q` or, without pytest, `python3 tests/test_pipeline.py`.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pipeline as p  # noqa: E402
from tracker import Tracker  # noqa: E402

GOOD_BODY = "## Evals\nx\n## Acceptance criteria\ny"


def issue(iid, state="Todo", labels=("ready-for-agent", "task"), body=GOOD_BODY):
    return {"id": iid, "state": state, "labels": list(labels), "body": body, "title": iid}


def test_gate():
    assert p.gate(issue("X-1")) == []
    assert p.gate(issue("X-1", body="## EVALS\n- e\n## Acceptance Criteria\n- a\n")) == []  # case-insensitive
    assert p.gate(issue("X-1", labels=("ready-for-agent",))) == ["label `task`"]
    assert p.gate(issue("X-1", body="Evals: x\nAcceptance criteria: y")) == [
        "section `## Evals` with content", "section `## Acceptance criteria` with content"]
    assert p.gate(issue("X-1", body="## Evals\n\n## Acceptance criteria\n- y\n")) == [
        "section `## Evals` with content"]  # headings alone are not a spec


def test_pick_order_and_filters():
    issues = [issue("X-9"), issue("X-3"), issue("X-12", state="In Progress"),
              issue("X-1", labels=("task",)), issue("X-5", state="Done")]
    assert p.pick(issues)["id"] == "X-12"  # resumed work first
    assert p.pick(issues[:2])["id"] == "X-3"  # then by number, not list order
    assert p.pick(issues[3:]) is None


def test_verdict_takes_the_last_line():
    assert p.verdict("... VERDICT: REJECTED\nmore\nVERDICT: APPROVED") == "APPROVED"
    assert p.verdict("VERDICT: APPROVED or VERDICT: REJECTED at the end") == "REJECTED"
    assert p.verdict("nothing") is None


def test_marks():
    review = "HIGH a.py:3 x\n- REPEATED: no retry per chapter\n**REPEATED:** no test\nVERDICT: REJECTED"
    assert p.marks("REPEATED", review) == ["no retry per chapter", "no test"]
    assert p.marks("BLOCKED", "Done.\nBLOCKED: the API has no error field") == ["the API has no error field"]
    assert p.marks("REPEATED", "this finding is not REPEATED: it is new") == []  # only at line start
    assert p.marks("BLOCKED", None) == []


def test_fill_keeps_braces_in_prompts():
    assert p.fill(["x", "{prompt}", "--model", "{model}"], prompt="use {json} and {model}", model="m") == [
        "x", "use {json} and {model}", "--model", "m"]  # inserted text is never substituted again


def test_tracker_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "A-1.md").write_text(
            "---\nid: A-1\ntitle: T\nstate: Todo\nlabels: [task, ready-for-agent]\n---\nBody\n")
        tr = Tracker(Path(d))
        tr.label("A-1", add="needs-info", remove="ready-for-agent")
        tr.set_state("A-1", "Done")
        tr.comment("A-1", "hello")
        i = tr.get("A-1")
        assert i["labels"] == ["task", "needs-info"] and i["state"] == "Done"
        assert i["body"].startswith("Body\n") and "## Pipeline log" in i["body"] and "hello" in i["body"]
        (Path(d) / "README.md").write_text("no front matter here\n")
        assert [x["id"] for x in tr.list()] == ["A-1"]  # a broken file is skipped, not fatal


def test_reviewer_fallback_ignores_stale_result():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "logs").mkdir()
        slow = "open('result.md','w').write('VERDICT: APPROVED'); import time; time.sleep(5)"
        cfg = {"work": d, "base": d, "max_rounds": 2, "repo": {"branch": "main"}, "reviewer": {
            "command": [sys.executable, "-c", slow, "{out}"], "command_name": "slow",
            "fallback": [sys.executable, "-c", "print('HIGH x\\nVERDICT: REJECTED')"], "fallback_name": "fallback",
            "timeout_minutes": 0.02}}
        text, who = p.review({"id": "X-1", "title": "t", "body": "b"}, d, "", 1, "", d / "logs", cfg)
        assert p.verdict(text) == "REJECTED" and who == "fallback"


def _deploy_cfg(d: Path, health: str) -> dict:
    return {"repo": {"path": d}, "deploy": {
        "snapshot": "cp live live.prev", "build": "echo v2 > next", "up": "cp next live",
        "health": health, "rollback": "cp live.prev live", "health_tries": 2, "health_interval_seconds": 0}}


def test_deploy_rolls_back_on_bad_health_check():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "live").write_text("v1\n")
        ok, msg = p.deploy(_deploy_cfg(d, "false"))
        assert not ok and "rolled back" in msg and (d / "live").read_text() == "v1\n"
        ok, _ = p.deploy(_deploy_cfg(d, "grep -q v2 live"))
        assert ok and (d / "live").read_text() == "v2\n"


def test_deploy_build_failure_keeps_old_version():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "live").write_text("v1\n")
        cfg = _deploy_cfg(d, "true")
        cfg["deploy"]["build"] = "exit 3"
        ok, msg = p.deploy(cfg)
        assert not ok and "build failed" in msg and (d / "live").read_text() == "v1\n"


def test_deploy_failed_up_rolls_back_and_failed_rollback_is_reported():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "live").write_text("v1\n")
        cfg = _deploy_cfg(d, "true")
        cfg["deploy"]["up"] = "cp next live && exit 1"  # half-applied, then fails
        ok, msg = p.deploy(cfg)
        assert not ok and "`up` exited 1; rolled back" in msg and (d / "live").read_text() == "v1\n"
        cfg["deploy"]["rollback"] = "exit 2"
        ok, msg = p.deploy(cfg)
        assert not ok and "ROLLBACK FAILED" in msg


def test_end_to_end_demo():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d) / "demo"
        subprocess.run([sys.executable, str(ROOT / "examples/setup_demo.py"), str(ws)], check=True, capture_output=True)
        r = subprocess.run([sys.executable, str(ROOT / "pipeline.py"), "--config", str(ws / "pipeline.toml"), "--all"],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        tr = Tracker(ws / "issues")
        one, two, three, four = (tr.get(f"DEMO-{n}") for n in (1, 2, 3, 4))
        assert one["state"] == "Done", one                               # happy path
        assert "needs-info" in two["labels"] and two["state"] == "Todo"  # stopped at the gate
        assert "ready-for-human" in three["labels"] and "BLOCKED" not in three["state"]
        assert "needs a decision: worker:" in three["body"]              # early escalation, no review spent
        assert four["state"] == "Done"                                   # rejected once, fixed, approved
        report = (ws / "reports").glob("DEMO-4-*.md").__next__().read_text()
        assert "| 1 | fail |" in report and "| 2 | pass |" in report and "APPROVED" in report
        log = subprocess.run(["git", "-C", str(ws / "origin.git"), "log", "--format=%s", "main"],
                             capture_output=True, text=True, check=True).stdout
        assert "(DEMO-1)" in log and "(DEMO-4)" in log and "DEMO-3" not in log
        assert "multiply" in (ws / "service/calc.py").read_text()        # deployed after health check


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
