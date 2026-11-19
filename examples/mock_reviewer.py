"""Deterministic stand-in for the reviewer agent: it runs in the review folder and reads the same files a
real reviewer gets (REVIEW.md, diff.patch, checks.txt). It rejects when any check failed or the diff has no
test, and approves otherwise, always ending with the `VERDICT:` line the pipeline parses."""

import re
from pathlib import Path

checks = Path("checks.txt").read_text(encoding="utf-8")
diff = Path("diff.patch").read_text(encoding="utf-8")
failed = [int(c) for c in re.findall(r"^\(exit (\d+)\)$", checks, re.M) if int(c)]
findings = []
if failed:
    findings.append("HIGH checks.txt: the test suite fails; the change does not do what the issue asks.")
if "tests/" not in diff:
    findings.append("HIGH diff.patch: no test covers the acceptance criteria.")
if Path("previous.md").exists() and findings:
    findings.append("REPEATED: " + findings[0])
print("\n".join(findings) or "No blocking findings.")
print("VERDICT: " + ("REJECTED" if findings else "APPROVED"))
