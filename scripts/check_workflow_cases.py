"""Offline workflow declarations and runtime-receipt consistency; no live execution."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "W10": "requirement-analyst", "W20": "implementer", "W30-red": "verifier",
    "W35": "diagnostician", "W36": "implementer", "W30-green": "verifier",
    "W41": "code-reviewer", "W42": "semantic-reviewer", "W43": "principle-reviewer",
    "W44-independent": "code-reviewer", "W45-query": "query-reviewer",
    "W50": "document-reviewer", "W60": "delivery-planner",
}


def local_file(base, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("invalid relative reference")
    p = (base / value).resolve()
    if not p.is_relative_to(base.resolve()) or not p.is_file():
        raise ValueError("missing or outside-scope reference")
    return p


def digest_map(pairs):
    return hashlib.sha256(json.dumps(pairs, sort_keys=True).encode()).hexdigest()


def check_workflow_case(folder):
    paths = list(folder.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("workflow case symlink")
    actual = {p.relative_to(folder).as_posix() for p in paths if p.is_file()}
    if not {"README.md", "case.json", "artifact-manifest.json"} <= actual:
        raise ValueError("workflow case files missing")
    case = json.loads((folder / "case.json").read_text())
    if (case["kind"] != "workflow_case" or case["case_id"] != folder.name
            or case["synthetic"] is not True):
        raise ValueError("invalid workflow case declaration")
    workflow = local_file(ROOT, case["workflow"])
    if workflow.parent != ROOT / "workflows" or workflow.suffix != ".md":
        raise ValueError("invalid workflow reference")
    stages = case["stages"]
    if [s["id"] for s in stages] != list(STAGES):
        raise ValueError("workflow stage order or membership mismatch")
    for stage in stages:
        if stage["agent"] != "agents/" + STAGES[stage["id"]] + ".md":
            raise ValueError("workflow stage Agent mismatch")
        local_file(ROOT, stage["agent"])
        if stage["status"] not in {"documented", "verified", "conditional_not_triggered", "pending_review", "reviewed", "ready_for_source_publication"}:
            raise ValueError("unknown stage status")
        for kind in ["inputs", "outputs"]:
            if not isinstance(stage[kind], list) or not stage[kind]:
                raise ValueError("stage handoff empty")
            for value in stage[kind]:
                local_file(folder, value)
    if case["execution_mode"] != "manual_role_adoption_with_separate_readonly_review":
        raise ValueError("unsupported execution identity")
    independent = next(s for s in stages if s["id"] == "W44-independent")
    if independent["status"] != "reviewed" or independent["review_scopes"] != ["code", "semantics", "principles", "documentation"]:
        raise ValueError("independent review scope pending or mismatched")
    if stages[-1]["status"] != "ready_for_source_publication":
        raise ValueError("source publication handoff not ready")
    ids = []
    for row in case["acceptance"]:
        ids.append(row["id"])
        if not row["expected"].strip():
            raise ValueError("empty acceptance")
        local_file(folder, row["evidence"])
    if ids != ["A" + str(i) for i in range(1, 8)]:
        raise ValueError("workflow acceptance identity mismatch")
    receipt = json.loads(local_file(folder, case["runtime_evidence"]).read_text())
    if receipt["synthetic"] is not True or receipt["status"] != "PASSED":
        raise ValueError("workflow receipt is not accepted red/green evidence")
    source_paths = [p for p in sorted((folder / "app").rglob("*")) if p.is_file()]
    source_paths += [local_file(folder, "fixtures/TagService-v1.java"), local_file(folder, "run.py")]
    sources = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in source_paths}
    identity = digest_map(sources)
    if (case["source_bundle_id"] != identity or receipt["source_bundle_id"] != identity
            or receipt["source_sha256"] != sources):
        raise ValueError("runtime source bundle drift")
    test = local_file(folder, "app/src/test/java/example/workflow/TagWorkflowTest.java").read_text()
    expected = re.findall(r"@Test\s+void\s+(\w+)\s*\(", test)
    if len(expected) != 13 or len(set(expected)) != 13:
        raise ValueError("expected test declaration mismatch")
    variants = receipt["variants"]
    if [v["variant"] for v in variants] != ["v1", "v2"]:
        raise ValueError("red/green variant order mismatch")
    for item in variants:
        pairs = {p.relative_to(folder / "app").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted((folder / "app").rglob("*")) if p.is_file()}
        if item["variant"] == "v1":
            pairs["src/main/java/example/workflow/TagService.java"] = sources["fixtures/TagService-v1.java"]
        if item["compiled_source_sha256"] != pairs or item["candidate_id"] != digest_map(pairs):
            raise ValueError("compiled candidate drift")
        failures = ["blankItemRejectsWholeRequest", "nullItemRejectsWholeRequest"] if item["variant"] == "v1" else []
        if (item["process_exit"] != (1 if item["variant"] == "v1" else 0)
                or item["tests"] != 13 or sorted(item["test_names"]) != sorted(expected)
                or item["failures"] != failures or item["errors"] or item["skipped"]
                or item["accepted"] is not True):
            raise ValueError("runtime test receipt inconsistent")
    if receipt["candidate_id"] != variants[1]["candidate_id"] or case["candidate_id"] != variants[1]["candidate_id"]:
        raise ValueError("reviewed candidate does not match green candidate")
    verification = case["verification"]
    if verification != {"java": "PASSED", "spring": "REAL_CONTEXT_AND_MOCKMVC",
                         "database": "not_connected", "native_agent": "not_run", "deployment": "not_run"}:
        raise ValueError("unexpected workflow runtime scope")
    before = local_file(folder, "fixtures/TagService-v1.java").read_text().splitlines(True)
    after = local_file(folder, "app/src/main/java/example/workflow/TagService.java").read_text().splitlines(True)
    difference = "".join(difflib.unified_diff(before, after,
                         fromfile="fixtures/TagService-v1.java",
                         tofile="app/src/main/java/example/workflow/TagService.java"))
    if local_file(folder, "change.diff").read_text() != difference:
        raise ValueError("workflow candidate diff drift")
    rows = json.loads((folder / "artifact-manifest.json").read_text())["files"]
    if {row["path"] for row in rows} != actual - {"artifact-manifest.json"} or len(rows) != len(actual) - 1:
        raise ValueError("workflow case manifest set mismatch")
    for row in rows:
        if hashlib.sha256(local_file(folder, row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("workflow case SHA drift")


def main():
    count = 0
    role = runpy.run_path(str(ROOT / "scripts/check_agent_cases.py"))
    graph = runpy.run_path(str(ROOT / "scripts/check_graph_cases.py"))
    build = runpy.run_path(str(ROOT / "scripts/check_spring_build_cases.py"))
    docker = runpy.run_path(str(ROOT / "scripts/check_docker_cases.py"))
    for folder in sorted((ROOT / "examples").iterdir()):
        if not folder.is_dir():
            continue
        if folder.name == "bookmark-title":
            continue  # Explicit legacy Java fixture, verified by scripts/check.py.
        declaration = json.loads(local_file(folder, "case.json").read_text())
        kind = declaration.get("kind", "role_case" if "agent" in declaration and "skill" in declaration else None)
        if kind == "workflow_case":
            check_workflow_case(folder)
            count += 1
        elif kind == "role_case":
            role["check_case"](folder)
        elif kind == "graph_case":
            graph["check_graph_case"](folder)
        elif kind == "spring_build_graph_case":
            build["check_spring_build_case"](folder)
        elif kind == "docker_spring_graph_case":
            docker["check_docker_case"](folder)
        elif kind == "native_spring_workflow_case":
            runpy.run_path(str(ROOT / "scripts/check_native_cases.py"))["check_native_case"](folder)
        else:
            raise ValueError("unknown example kind")
    print(f"PASS: {count} workflow cases; stage declarations, source identities and receipt consistency; no tests executed")


if __name__ == "__main__":
    main()
