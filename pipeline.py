#!/usr/bin/env python3
"""Issue-to-deploy pipeline driven by coding agents, with a gate, cross-vendor review and rollback.

One issue at a time:
  1. gate     - the issue needs the `task` label plus `## Evals` and `## Acceptance criteria` sections,
                otherwise it leaves the queue with `needs-info` and a comment saying what is missing;
  2. worker   - a coding agent (Claude Code by default) implements it in its own git worktree/branch,
                without docker, sudo or push;
  3. checks   - the pipeline itself runs the project's tests/lint/build (the agent's claims don't count);
  4. review   - an agent from another vendor (Codex by default) reviews diff + check output and must end
                with `VERDICT: APPROVED|REJECTED`; rejections go back to the worker, up to N rounds;
                a repeated blocking finding or an impossible spec escalates to a human early;
  5. integrate- rebase + fast-forward push, then an optional deploy with backup, health check and
                automatic rollback to the previous image;
  6. report   - Markdown report per issue, a log line, an optional webhook message.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import unicodedata
import urllib.request
from pathlib import Path

from tracker import Tracker

QUEUE_LABEL = "ready-for-agent"
def find_bash() -> str:
    """POSIX bash for the checks and git steps. On Windows that must be Git Bash: the `bash` launchers in
    System32 and WindowsApps start WSL, a different machine with different files."""
    if os.environ.get("PIPELINE_BASH"):
        return os.environ["PIPELINE_BASH"]
    if os.name != "nt":
        return shutil.which("bash") or "bash"
    git = shutil.which("git")
    if git:
        for up in (Path(git).parent.parent, Path(git).parent.parent.parent):  # <Git>/cmd or <Git>/mingw64/bin
            if (up / "bin" / "bash.exe").is_file():
                return str(up / "bin" / "bash.exe")
    found = shutil.which("bash")
    if found and not re.search(r"(?i)\\(system32|windowsapps)\\", found):
        return found
    raise SystemExit("Git Bash not found: install Git for Windows or set PIPELINE_BASH")


BASH = find_bash()


class QuotaHit(Exception):
    """The agent's plan or API quota ran out: wait and retry, don't fail the issue."""


class AgentAuth(Exception):
    """The agent CLI is logged out: only a human can fix it."""


def log(msg: str) -> None:
    print(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def sh(cmd: str, cwd: Path | None = None, timeout: int = 1800, check: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run([BASH, "-c", cmd], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f"{cmd!r} exited {r.returncode}: {(r.stderr or r.stdout)[-800:]}")
    return r


# --------------------------------------------------------------------------- config


def load_config(path: Path) -> dict:
    cfg = tomllib.loads(path.read_text(encoding="utf-8"))
    base = path.resolve().parent
    for key in ("issues", "reports", "work"):
        cfg[key] = (base / cfg.get(key, key)).resolve()
    cfg["repo"]["path"] = (base / cfg["repo"]["path"]).resolve()
    cfg["repo"].setdefault("branch", "main")
    cfg["repo"].setdefault("setup", [])
    cfg.setdefault("max_rounds", 4)
    cfg.setdefault("poll_seconds", 300)
    cfg["base"] = base
    return cfg


def fill(args: list[str], **values: str) -> list[str]:
    """Single-pass placeholder substitution: text inserted for one placeholder (e.g. an issue body that
    mentions `{model}`) is never substituted again, and unknown braces are left alone."""
    return [re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), a) for a in args]


# --------------------------------------------------------------------------- queue


def _plain(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def gate(issue: dict) -> list[str]:
    """What the issue is missing to enter the queue (empty list = good to go)."""
    body = _plain(issue.get("body") or "")
    missing = []
    if "task" not in issue["labels"]:
        missing.append("label `task`")
    for title, pattern in (("Evals", r"evals"), ("Acceptance criteria", r"acceptance criteria")):
        # The section must exist and have content before the next heading.
        m = re.search(rf"^##\s*{pattern}\b[^\n]*\n(.*?)(?=^#|\Z)", body, re.M | re.S)
        if not m or not m.group(1).strip():
            missing.append(f"section `## {title}` with content")
    return missing


def _number(iid: str) -> int:
    m = re.search(r"(\d+)$", iid)
    return int(m.group(1)) if m else 0


def pick(issues: list[dict]) -> dict | None:
    """One issue at a time: resumed ones (In Progress) first, then Todo, by issue number."""
    ok = [i for i in issues if QUEUE_LABEL in i["labels"] and i["state"] in ("Todo", "In Progress")]
    ok.sort(key=lambda i: (i["state"] != "In Progress", _number(i["id"])))
    return ok[0] if ok else None


# --------------------------------------------------------------------------- agents


METER = {"cost_usd": 0.0, "tokens": 0, "agent_calls": 0}  # per issue; reset in process()


def meter(stdout: str, stderr: str) -> str:
    """Account cost/tokens and return the agent's answer text.

    Claude Code with `--output-format json` prints one JSON object with `result`, `total_cost_usd` and `usage`;
    Codex prints `tokens used` followed by the count. Anything else is taken as plain text."""
    METER["agent_calls"] += 1
    m = re.search(r"tokens used\s*\n?\s*(\d[\d.,]*)", stderr + stdout)
    if m:  # Codex prints the count with the locale's thousands separator (`2,827` or `2.827`)
        METER["tokens"] += int(re.sub(r"\D", "", m.group(1)))
    try:
        data = json.loads(stdout)
    except ValueError:
        return stdout
    if not isinstance(data, dict) or "result" not in data:
        return stdout
    METER["cost_usd"] += float(data.get("total_cost_usd") or 0)
    u = data.get("usage") or {}
    METER["tokens"] += sum(int(u.get(k) or 0) for k in (
        "input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return str(data.get("result") or "")


def run_agent(command: list[str], cwd: Path, logfile: Path, timeout: float) -> str:
    exe = shutil.which(command[0]) or command[0]  # finds npm `.cmd` shims on Windows too
    r = subprocess.run([exe, *command[1:]], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    logfile.write_text(out, encoding="utf-8")
    if re.search(r"(?i)failed to authenticate|session expired|not logged in|please run /login", out) and (
            r.returncode or '"is_error":true' in out.replace(" ", "")):
        raise AgentAuth(out.strip()[-200:])
    if r.returncode and re.search(r"(?i)usage limit|rate limit|limit reached|resets at", out[-2000:]):
        raise QuotaHit(out[-300:])
    return meter(r.stdout or "", r.stderr or "")


def verdict(text: str) -> str | None:
    """The last `VERDICT:` line wins (reviewers sometimes quote the format earlier in the text)."""
    m = re.findall(r"VERDICT:\s*(APPROVED|REJECTED)", text or "")
    return m[-1] if m else None


def marks(tag: str, text: str | None) -> list[str]:
    """`TAG: reason` lines at the start of a line (BLOCKED from the worker, REPEATED from the reviewer)."""
    return [m.strip() for m in re.findall(rf"(?m)^\W*{tag}[*_]*:[*_\s]*(.+?)\s*$", text or "")]


WORKER_PROMPT = """You are the worker of an automated pipeline. Implement issue {iid} in this repository
(a git worktree on branch {branch}). Read the repository's CLAUDE.md or AGENTS.md first, if there is one.

Rules: work only inside this folder; do not run docker, do not push, do not touch production. Cover every
acceptance criterion with a test that fails without your change. Run the project's checks. When done, commit
everything with a Conventional Commits message that mentions {iid}. Leave nothing uncommitted.

If an acceptance criterion or eval is impossible (for example, it depends on data an external API does not
return), do not fake it: implement the rest and end your answer with one line `BLOCKED: <reason>` per item.

# Issue {iid}: {title}

{body}
{feedback}"""

REVIEW_PROMPT = """You are a senior reviewer. Review the change for the issue below.

Files in this folder: `diff.patch` (diff against the main branch), `checks.txt` (real output of tests and
build, which you cannot run yourself), `PROJECT_RULES.md` (the repository's rules for agents, when it has
any) and this issue. Round {round} of at most {max_rounds}.{previous}

Check: every acceptance criterion and eval is really met; the change follows the project rules;
correctness, concurrency and data-loss bugs; security proportional to the project; tests that would fail
without the change. Ignore style. `checks.txt` is ground truth: do not claim a test fails when it shows the
suite passing, and do not reject on arithmetic you cannot verify; when unsure, say so and keep it MEDIUM.

Format: findings with severity (CRITICAL/HIGH/MEDIUM/LOW), file:line, a concrete scenario and the fix.
The last line must be exactly `VERDICT: APPROVED` or `VERDICT: REJECTED`.

Verdict rule, no exceptions: REJECTED only for a CRITICAL or HIGH finding, an unmet acceptance criterion or
eval, or failing checks. MEDIUM/LOW findings alone do not reject: list them and approve (they become
follow-up issues). If a MEDIUM is serious enough to reject, call it HIGH.

If a CRITICAL/HIGH finding or unmet criterion from the previous round is still unresolved, write
`REPEATED: <short summary>` for each one before the verdict. New findings don't get that mark.

# Issue {iid}: {title}

{body}
"""


# --------------------------------------------------------------------------- steps


def prepare(iid: str, cfg: dict) -> tuple[Path, str]:
    repo, branch = cfg["repo"]["path"], f"pipeline/{iid}"
    wt = cfg["work"] / "wt" / iid
    sh(f"git -C '{repo}' fetch -q origin", check=True)
    if wt.is_dir() and sh("git rev-parse --is-inside-work-tree", cwd=wt).returncode == 0:
        log(f"{iid}: resuming the existing worktree")  # e.g. after a quota pause; keep the work done so far
        return wt, branch
    sh(f"git -C '{repo}' worktree prune")
    if sh(f"git -C '{repo}' rev-parse --verify -q refs/heads/{branch}").returncode == 0:
        sh(f"git -C '{repo}' worktree add -q '{wt}' {branch}", check=True)  # branch survived, worktree did not
    else:
        sh(f"git -C '{repo}' worktree add -q -b {branch} '{wt}' origin/{cfg['repo']['branch']}", check=True)
    for step in cfg["repo"]["setup"]:
        sh(step, cwd=wt, check=True)
    return wt, branch


def run_checks(wt: Path, cfg: dict) -> tuple[bool, str]:
    out, ok = [], True
    for cmd in cfg["repo"]["checks"]:
        r = sh(f"set -o pipefail; {cmd}", cwd=wt, timeout=1200)
        ok &= r.returncode == 0
        out.append(f"$ {cmd}\n(exit {r.returncode})\n{(r.stdout + r.stderr).strip()[-2500:]}")
    return ok, "\n\n".join(out)


def review(issue: dict, wt: Path, checks: str, rnd: int, previous: str, logdir: Path, cfg: dict) -> tuple[str, str]:
    iid, rc = issue["id"], cfg["reviewer"]
    diff = sh(f"git diff origin/{cfg['repo']['branch']}...HEAD", cwd=wt).stdout
    prompt = REVIEW_PROMPT.format(
        round=rnd, max_rounds=cfg["max_rounds"], iid=iid, title=issue.get("title", ""), body=issue["body"],
        previous=("\n\nYour previous round is in `previous.md`; check whether its findings were fixed."
                  if previous else ""),
    )
    # The reviewer gets a fresh folder with files only: it never sees the worktree, so it cannot edit it.
    rdir = cfg["work"] / "review" / iid
    shutil.rmtree(rdir, ignore_errors=True)
    rdir.mkdir(parents=True)
    files = {"REVIEW.md": prompt, "diff.patch": diff, "checks.txt": checks}
    rules = [(wt / n).read_text(encoding="utf-8", errors="replace") for n in ("CLAUDE.md", "AGENTS.md")
             if (wt / n).is_file()]
    if rules:  # without them the reviewer approved code that broke a rule it never saw (see the benchmark)
        files["PROJECT_RULES.md"] = "\n\n".join(rules)
    if previous:
        files["previous.md"] = previous
    for name, content in files.items():
        (rdir / name).write_text(content, encoding="utf-8")
    timeout = float(rc.get("timeout_minutes", 40)) * 60
    text, who = "", ""
    for name in ("command", "fallback"):
        if not rc.get(name):
            continue
        out = rdir / "result.md"
        out.unlink(missing_ok=True)  # never read a verdict left behind by the previous command
        cmd = fill(rc[name], out=str(out), python=sys.executable, base=str(cfg["base"]))
        try:
            stdout = run_agent(cmd, rdir, logdir / f"review-{rnd}-{name}.log", timeout)
        except (OSError, subprocess.TimeoutExpired) as e:
            log(f"reviewer {name} failed: {e}")
            continue
        text = out.read_text(encoding="utf-8", errors="replace") if out.exists() else stdout
        who = rc.get(f"{name}_name") or Path(cmd[0]).name
        if verdict(text):
            break
        log(f"reviewer {name} gave no verdict")
    (logdir / f"review-{rnd}.md").write_text(text, encoding="utf-8")
    return text, who


def deploy(cfg: dict) -> tuple[bool, str]:
    """Backup + snapshot of the running version, build, up, health check; a bad health check rolls back."""
    d = cfg.get("deploy")
    if not d:
        return True, "no deploy configured"
    cwd = cfg["repo"]["path"]
    for step in ("backup", "snapshot"):
        if d.get(step):
            sh(d[step], cwd=cwd, check=True)
    b = sh(f"set -o pipefail; {d['build']}", cwd=cwd, timeout=1800)
    if b.returncode:  # the old version is still up and would pass the health check: that is not success
        return False, f"build failed; production stays on the previous version.\n{(b.stdout + b.stderr)[-500:]}"
    up = sh(d["up"], cwd=cwd)
    if up.returncode == 0:
        for _ in range(int(d.get("health_tries", 30))):
            if sh(d["health"], cwd=cwd).returncode == 0:
                return True, "deployed, health check ok"
            time.sleep(float(d.get("health_interval_seconds", 2)))
    why = "health check failed" if up.returncode == 0 else f"`up` exited {up.returncode}"
    rb = sh(d["rollback"], cwd=cwd)
    if rb.returncode:
        return False, (f"{why} AND ROLLBACK FAILED (exit {rb.returncode}): production may be down.\n"
                       f"{(rb.stdout + rb.stderr)[-500:]}")
    return False, f"{why}; rolled back to the previous version (backup kept)"


def integrate(wt: Path, cfg: dict) -> str:
    """Rebase on the remote branch and fast-forward push. Returns the pushed commit."""
    rb = cfg["repo"]["branch"]
    before = sh("git rev-parse HEAD", cwd=wt).stdout.strip()
    sh(f"git fetch -q origin && git rebase -q origin/{rb}", cwd=wt, check=True)
    if sh("git rev-parse HEAD", cwd=wt).stdout.strip() != before:
        # The branch moved while the agents worked: the combination was never tested, so test it now.
        ok, checks = run_checks(wt, cfg)
        if not ok:
            raise RuntimeError(f"checks fail after rebasing on {rb}; nothing pushed.\n{checks[-800:]}")
    sh(f"git push -q origin HEAD:{rb}", cwd=wt, check=True)
    return sh("git rev-parse --short HEAD", cwd=wt).stdout.strip()


def refresh_main_clone(head: str, cfg: dict) -> None:
    """Fast-forward the clone the deploy runs from; refuse (after the push) if someone left it dirty."""
    rb, repo = cfg["repo"]["branch"], cfg["repo"]["path"]
    clean = not sh("git status --porcelain --untracked-files=no", cwd=repo).stdout.strip()
    on_branch = sh("git branch --show-current", cwd=repo).stdout.strip() == rb
    if not (clean and on_branch):
        raise RuntimeError(f"pushed {head}, but {repo} is not clean on {rb}: deploy left to a human")
    sh(f"git pull -q --ff-only origin {rb}", cwd=repo, check=True)


def cleanup_worktree(iid: str, cfg: dict) -> None:
    repo = cfg["repo"]["path"]
    sh(f"git -C '{repo}' worktree remove --force '{cfg['work'] / 'wt' / iid}'; git -C '{repo}' worktree prune; "
       f"git -C '{repo}' branch -D pipeline/{iid}")
    shutil.rmtree(cfg["work"] / "review" / iid, ignore_errors=True)


def notify(cfg: dict, text: str) -> None:
    url = os.environ.get(cfg.get("notify", {}).get("webhook_env", "PIPELINE_WEBHOOK"), "")
    if not url:
        return
    req = urllib.request.Request(url, data=json.dumps({"content": text[:1900]}).encode(),
                                 headers={"content-type": "application/json", "user-agent": "agent-issue-pipeline"})
    try:
        urllib.request.urlopen(req, timeout=15).close()
    except OSError as e:
        log(f"webhook failed: {e}")


def process(issue: dict, tr: Tracker, cfg: dict, dry: bool = False) -> str:
    iid = issue["id"]
    missing = gate(issue)
    if missing:
        log(f"{iid} stopped at the gate: {missing}")
        if not dry:
            tr.label(iid, add="needs-info", remove=QUEUE_LABEL)
            tr.comment(iid, f"Pipeline: not queued. Missing {', '.join(missing)}. Fix it and add `{QUEUE_LABEL}` back.")
        return "gate"
    if dry:
        log(f"{iid} would pass the gate (dry run)")
        return "dry"
    tr.set_state(iid, "In Progress")
    METER.update(cost_usd=0.0, tokens=0, agent_calls=0)
    started = time.monotonic()
    wc = cfg["worker"]
    model = next((lb.split(":", 1)[1] for lb in issue["labels"] if lb.startswith("model:")), wc.get("model", ""))
    logdir = cfg["work"] / "logs" / iid / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    logdir.mkdir(parents=True)
    wt, branch = prepare(iid, cfg)
    log(f"{iid} started ({model or 'default model'}) in {wt}")

    feedback, previous, rounds, stuck = "", "", [], []
    approved, who, text = False, "", ""
    for rnd in range(1, cfg["max_rounds"] + 1):
        prompt = WORKER_PROMPT.format(iid=iid, branch=branch, title=issue.get("title", ""), body=issue["body"],
                                      feedback=feedback)
        try:
            out = run_agent(fill(wc["command"], prompt=prompt, model=model, python=sys.executable,
                                 base=str(cfg["base"])),
                            wt, logdir / f"worker-{rnd}.log", float(wc.get("timeout_minutes", 90)) * 60)
        except subprocess.TimeoutExpired as e:
            # Partial work from a worker that ran out of time is never integrated automatically.
            partial = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            (logdir / f"worker-{rnd}.log").write_text(partial, encoding="utf-8")
            stuck = [f"worker: {m}" for m in marks("BLOCKED", partial)] + [
                f"worker: timed out after {wc.get('timeout_minutes', 90)} min"]
            rounds.append(f"| {rnd} | - | - | worker timed out |")
            log(f"{iid} round {rnd}: worker timed out; escalating")
            break
        sh("git add -A && git diff --cached --quiet || git commit -q -m 'chore: worker leftovers'", cwd=wt)
        if not sh(f"git diff --stat origin/{cfg['repo']['branch']}...HEAD", cwd=wt).stdout.strip():
            # Nothing changed: skip the checks and the reviewer's quota.
            rounds.append(f"| {rnd} | - | - | worker changed nothing |")
            stuck = [f"worker: {m}" for m in marks("BLOCKED", out)]
            if stuck:
                break
            feedback = "\n\n# Previous round\n\nNothing was committed. Implement the issue and commit."
            continue
        ok, checks = run_checks(wt, cfg)
        (logdir / f"checks-{rnd}.txt").write_text(checks, encoding="utf-8")
        text, who = review(issue, wt, checks, rnd, previous, logdir, cfg)
        v = verdict(text) if ok else "REJECTED"
        rounds.append(f"| {rnd} | {'pass' if ok else 'fail'} | {who} | {v or 'no verdict'} |")
        log(f"{iid} round {rnd}: checks {'pass' if ok else 'fail'}, {who}: {v}")
        # Early escalation: the worker says part of the spec is impossible (even if the reviewer approved the
        # rest), or the same blocking finding survived a round of fixes. More rounds would only burn quota.
        stuck = [f"worker: {m}" for m in marks("BLOCKED", out)]
        if v == "APPROVED" and ok and not stuck:
            approved = True
            break
        stuck += [f"reviewer: {m}" for m in marks("REPEATED", text)]
        if stuck:
            log(f"{iid} round {rnd}: early escalation: {stuck}")
            break
        previous = text
        feedback = ("\n\n# Previous round rejected\n\nFix everything below and keep what was already right.\n\n"
                    + ("## Checks\n\n" + checks + "\n\n" if not ok else "") + "## Review\n\n" + text)

    date = dt.date.today().isoformat()
    tr.label(iid, remove=QUEUE_LABEL)  # never re-enters the queue on its own
    head = ""  # set once the change is on the remote branch, whatever happens afterwards
    if not approved:
        tr.label(iid, add="ready-for-human")
        why = ("; needs a decision: " + " | ".join(stuck)) if stuck else ""
        result = f"{'escalated' if stuck else 'rejected'} after {len(rounds)} round(s)"
        tr.comment(iid, f"Pipeline: {result}{why}; branch `{branch}`.")
    else:
        try:
            head = integrate(wt, cfg)
            refresh_main_clone(head, cfg)
            deployed, msg = deploy(cfg)
            result = f"approved and merged (`{head}`); {msg}"
        except RuntimeError as e:
            deployed, result = False, f"approved, but integration stopped: {e}"
        tr.set_state(iid, "Done" if deployed else "In Review")
        tr.comment(iid, f"Pipeline: {result}")
        if deployed:
            cleanup_worktree(iid, cfg)
        else:
            tr.label(iid, add="ready-for-human")
    minutes = (time.monotonic() - started) / 60
    usage = (f"{minutes:.1f} min, {METER['agent_calls']} agent calls, {METER['tokens']:,} tokens, "
             f"US$ {METER['cost_usd']:.2f} reported by the agent CLIs")
    cfg["reports"].mkdir(parents=True, exist_ok=True)
    (cfg["reports"] / f"{iid}-{date}.md").write_text(
        f"# {iid}: {issue.get('title', '')}\n\n**Result:** {result}\n\n**Usage:** {usage}\n\n"
        f"| Round | Checks | Reviewer | Verdict |\n|---|---|---|---|\n" + "\n".join(rounds)
        + f"\n\n## Last review\n\n{text}\n", encoding="utf-8")
    (cfg["reports"] / f"{iid}.json").write_text(json.dumps({
        "id": iid, "outcome": "approved" if approved else ("escalated" if stuck else "rejected"),
        "merged": bool(head), "head": head or None, "rounds": len(rounds), "stuck": stuck,
        "minutes": round(minutes, 2), **METER}, indent=2), encoding="utf-8")
    with open(cfg["reports"] / "pipeline-log.md", "a", encoding="utf-8") as f:
        f.write(f"- {date} {iid} {issue.get('title', '')}: {result} ({usage})\n")
    notify(cfg, f"{'✅' if approved else '⚠️'} **{iid}** {issue.get('title', '')}\n{result}")
    log(f"{iid} finished: {result}")
    return "approved" if approved else "rejected"


def loop(cfg: dict, once: bool, dry: bool, only: str | None) -> None:
    tr, paused = Tracker(cfg["issues"]), False
    while True:
        try:
            cand = tr.get(only) if only else pick(tr.list())
            if cand:
                process(cand, tr, cfg, dry)
                paused = False
                if not once:
                    continue  # there may be more in the queue: look again right away
        except (QuotaHit, AgentAuth) as e:
            why = "agent CLI logged out (log in again)" if isinstance(e, AgentAuth) else "agent quota exhausted"
            log(f"{why}: waiting 30 min ({e})")
            if not paused:  # one message per pause, not one every 30 minutes
                notify(cfg, f"⏸️ pipeline paused: {why}; retrying every 30 min.")
            paused = True
            if once:
                return
            time.sleep(1800)
            continue
        except Exception as e:  # one bad issue must not take the service down
            log(f"error: {type(e).__name__}: {e}")
            notify(cfg, f"❌ pipeline: {type(e).__name__}: {str(e)[:500]}")
            if once:
                raise
        if once:
            return
        time.sleep(cfg["poll_seconds"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=Path("pipeline.toml"))
    ap.add_argument("--once", action="store_true", help="process at most one issue and exit")
    ap.add_argument("--all", action="store_true", help="process the queue until it is empty, then exit")
    ap.add_argument("--dry-run", action="store_true", help="only run the gate, change nothing")
    ap.add_argument("--issue", help="process this issue (e.g. DEMO-1)")
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.all:
        tr = Tracker(cfg["issues"])
        while (cand := pick(tr.list())) is not None:
            process(cand, tr, cfg, a.dry_run)
            if a.dry_run:
                break
        return
    # A dry run changes nothing, so looping would pick the same issue forever: one pass only.
    loop(cfg, a.once or bool(a.issue) or a.dry_run, a.dry_run, a.issue)


if __name__ == "__main__":
    main()
