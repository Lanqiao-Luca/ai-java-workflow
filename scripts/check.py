"""Offline consistency checks for the three documentation layers."""
from pathlib import Path
from urllib.parse import unquote
import json
import hashlib
import difflib
import os
import re

ROOT = Path(__file__).resolve().parents[1]

def main():
    paths = []
    for directory, subdirs, names in os.walk(ROOT, followlinks=False):
        # Git metadata is never part of the public content manifest.
        if Path(directory) == ROOT:
            subdirs[:] = [n for n in subdirs if n != ".git"]
            names = [n for n in names if n != ".git"]
        paths.extend(Path(directory) / n for n in subdirs + names)
    if any(p.is_symlink() for p in paths):
        raise ValueError("unexpected symlink")
    actual = {p.relative_to(ROOT).as_posix() for p in paths if p.is_file()}
    rows = json.loads((ROOT / "public-manifest.json").read_text())["files"]
    declared = {r["path"] for r in rows}
    if actual != declared or len(rows) != len(declared):
        raise ValueError("manifest mismatch")
    if any(r["status"] != "reviewed_candidate" for r in rows):
        raise ValueError("unreviewed candidate entry")
    if any(part.startswith(".") for n in actual for part in Path(n).parts):
        raise ValueError("unexpected hidden file")
    links = 0
    for p in paths:
        if p.suffix != ".md":
            continue
        text = p.read_text()
        targets = []
        for m in re.finditer(r"\]\(([^)]+)\)", text):
            dest = unquote(m.group(1).strip("<>"))
            if ":" in dest or dest.startswith("/") or "#" in dest:
                raise ValueError("nonportable or unsupported link")
            q = (p.parent / dest).resolve()
            if not q.is_relative_to(ROOT) or not q.is_file():
                raise ValueError("broken local reference")
            targets.append(q)
            links += 1
        rel = p.relative_to(ROOT)
        if rel.parts[0] == "standards" and p.name != "README.md":
            for field in ["目的：", "## 适用条件", "## 输入", "## 操作步骤",
                          "## 输出", "## 角色职责", "## 验收方法", "## 异常与停止"]:
                if field not in text:
                    raise ValueError("incomplete method contract")
        if rel.parts[0] == "skills" and p.name == "SKILL.md":
            if not text.startswith("---\nname:") or not any(
                    q.relative_to(ROOT).parts[0] == "standards" for q in targets):
                raise ValueError("skill lacks method dependency")
            if any(q.relative_to(ROOT).parts[0] == "agents" for q in targets):
                raise ValueError("skill reverses responsibility dependency")
        if rel.parts[0] == "agents" and p.name != "README.md":
            if not any(q.name == "SKILL.md" for q in targets):
                raise ValueError("role lacks skill dependency")
            if any(q.relative_to(ROOT).parts[0] == "standards" for q in targets):
                raise ValueError("role bypasses skill")
    case = ROOT / "examples/bookmark-title"
    identity = json.loads((case / "artifact-manifest.json").read_text())["files"]
    expected = {"task.json", "before/BookmarkService.java", "after/BookmarkService.java",
                "tests/BookmarkServiceTest.java", "run.py", "change.diff"}
    if {row["path"] for row in identity} != expected or len(identity) != len(expected):
        raise ValueError("case identity set mismatch")
    for row in identity:
        if hashlib.sha256((case / row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("case identity drift")
    before = (case / "before/BookmarkService.java").read_text().splitlines(True)
    after = (case / "after/BookmarkService.java").read_text().splitlines(True)
    difference = "".join(difflib.unified_diff(before, after,
                         fromfile="before/BookmarkService.java", tofile="after/BookmarkService.java"))
    if (case / "change.diff").read_text() != difference:
        raise ValueError("case diff drift")
    print(f"PASS: {len(actual)} files, {links} local links, method fields, layer dependencies, case identities and diff")

if __name__ == "__main__":
    main()
