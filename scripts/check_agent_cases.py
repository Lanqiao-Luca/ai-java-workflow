"""Offline case structure and byte-identity checks; not semantic acceptance."""
from pathlib import Path
import hashlib
import json
import runpy

ROOT = Path(__file__).resolve().parents[1]


def local_file(base, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("invalid relative file reference")
    target = (base / value).resolve()
    if not target.is_relative_to(base.resolve()) or not target.is_file():
        raise ValueError("missing or out-of-scope file reference")
    return target


def check_case(folder):
    paths = list(folder.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("case symlink is not supported")
    required = {"README.md", "case.json", "trace.md", "result.md", "artifact-manifest.json"}
    actual = {p.relative_to(folder).as_posix() for p in paths if p.is_file()}
    if not required <= actual:
        raise ValueError("case chain files missing")
    case = json.loads((folder / "case.json").read_text())
    if case["case_id"] != folder.name or case["synthetic"] is not True:
        raise ValueError("case identity or synthetic declaration invalid")
    if case["mode"] not in {"document_walkthrough", "static_code_review"}:
        raise ValueError("unsupported case mode")
    agent = local_file(ROOT, case["agent"])
    skill = local_file(ROOT, case["skill"])
    if agent.parent != ROOT / "agents" or agent.suffix != ".md":
        raise ValueError("invalid Agent reference")
    if not skill.is_relative_to(ROOT / "skills") or skill.name != "SKILL.md":
        raise ValueError("invalid Skill reference")
    for field in ["inputs", "outputs"]:
        if not isinstance(case[field], list) or not case[field]:
            raise ValueError("empty case inputs or outputs")
        for name in case[field]:
            local_file(folder, name)
    acceptance = case["acceptance"]
    if not isinstance(acceptance, list) or not acceptance:
        raise ValueError("missing acceptance declaration")
    ids = []
    for row in acceptance:
        if not isinstance(row["id"], str) or not row["id"]:
            raise ValueError("invalid acceptance id")
        ids.append(row["id"])
        if not isinstance(row["expected"], str) or not row["expected"].strip():
            raise ValueError("empty expected result")
        local_file(folder, row["evidence"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate acceptance ids")
    verification = case["verification"]
    if (verification["java"] not in {"NOT_RUN", "not_applicable"}
            or verification["database"] not in {"not_connected", "local_sqlite_memory_only"}
            or verification["native_agent"] != "not_run"):
        raise ValueError("unsupported runtime declaration")
    if verification["database"] == "local_sqlite_memory_only":
        local_file(folder, "replay.py")
        local_file(folder, "fixture.json")
    rows = json.loads((folder / "artifact-manifest.json").read_text())["files"]
    declared = {row["path"] for row in rows}
    if declared != actual - {"artifact-manifest.json"} or len(rows) != len(declared):
        raise ValueError("case manifest file set mismatch")
    for row in rows:
        target = local_file(folder, row["path"])
        if hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("case SHA drift")


def main():
    count, workflows, graphs = 0, 0, 0
    workflow = runpy.run_path(str(ROOT / "scripts/check_workflow_cases.py"))
    graph = runpy.run_path(str(ROOT / "scripts/check_graph_cases.py"))
    for folder in sorted((ROOT / "examples").iterdir()):
        if not folder.is_dir():
            continue
        if folder.name == "bookmark-title":
            if (folder / "case.json").exists():
                raise ValueError("legacy Java example has an unexpected type declaration")
            continue  # Explicit legacy Java case, checked by scripts/check.py.
        declaration = json.loads(local_file(folder, "case.json").read_text())
        kind = declaration.get("kind", "role_case" if "agent" in declaration and "skill" in declaration else None)
        if kind == "role_case":
            check_case(folder)
            count += 1
        elif kind == "workflow_case":
            workflow["check_workflow_case"](folder)
            workflows += 1
        elif kind == "graph_case":
            graph["check_graph_case"](folder)
            graphs += 1
        else:
            raise ValueError("unknown example kind")
    print(f"PASS: {count} role cases, {workflows} workflow cases, {graphs} Graph cases; structure, identities and receipt consistency only")


if __name__ == "__main__":
    main()
