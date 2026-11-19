"""A tiny issue tracker kept as Markdown files in a folder (one file per issue).

File format (`issues/DEMO-1.md`):

    ---
    id: DEMO-1
    title: Add subtract()
    state: Todo
    labels: [task, ready-for-agent]
    ---
    Issue body in Markdown.

The pipeline only needs list/get, label add/remove, state changes and comments, so any real tracker
(GitHub Issues, Linear, Jira) can replace this module by implementing the same five functions.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

_FRONT = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.S)


def _parse(path: Path) -> dict:
    m = _FRONT.match(path.read_text(encoding="utf-8"))
    if not m:
        raise ValueError(f"{path}: missing front matter")
    meta: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = (s.strip() for s in line.split(":", 1))
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key] = value
    meta.setdefault("labels", [])
    meta.setdefault("state", "Todo")
    meta["id"] = meta.get("id") or path.stem
    meta["body"] = m.group(2)
    meta["path"] = path
    return meta


def _save(issue: dict) -> None:
    head = [f"id: {issue['id']}", f"title: {issue.get('title', '')}", f"state: {issue['state']}",
            f"labels: [{', '.join(issue['labels'])}]"]
    issue["path"].write_text("---\n" + "\n".join(head) + "\n---\n" + issue["body"], encoding="utf-8")


class Tracker:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def list(self) -> list[dict]:
        issues = []
        for p in sorted(self.folder.glob("*.md")):
            try:
                issues.append(_parse(p))
            except ValueError as e:  # one broken file (or a README) must not block the whole queue
                print(f"tracker: skipping {e}", file=sys.stderr)
        return issues

    def get(self, iid: str) -> dict:
        return _parse(self.folder / f"{iid}.md")

    def set_state(self, iid: str, state: str) -> None:
        issue = self.get(iid)
        issue["state"] = state
        _save(issue)

    def label(self, iid: str, add: str | None = None, remove: str | None = None) -> None:
        issue = self.get(iid)
        if remove in issue["labels"]:
            issue["labels"].remove(remove)
        if add and add not in issue["labels"]:
            issue["labels"].append(add)
        _save(issue)

    def comment(self, iid: str, text: str) -> None:
        issue = self.get(iid)
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        if "\n## Pipeline log\n" not in issue["body"]:
            issue["body"] = issue["body"].rstrip("\n") + "\n\n## Pipeline log\n"
        issue["body"] += f"\n- {stamp}: {text}\n"
        _save(issue)
