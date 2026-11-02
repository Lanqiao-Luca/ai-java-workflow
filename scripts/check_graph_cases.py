"""Verify Graph case declarations, byte identities and recorded results; do not execute."""
from pathlib import Path
import ast
import hashlib
import json
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]
PROBES = {"positive_write", "outside_read_denied", "outside_write_denied",
          "git_admin_read_denied", "git_admin_write_denied", "network_denied", "outside_hardlink_denied",
          "outside_symlink_read_denied", "fork_denied", "detached_child_denied"}


def local_file(base, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("invalid relative evidence path")
    path = (base / value).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise ValueError("missing or out-of-scope evidence")
    return path


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def source_map(names):
    return {name: hashlib.sha256(local_file(ROOT, name).read_bytes()).hexdigest() for name in names}


def probe(value):
    if set(value) != PROBES or any(item is not True for item in value.values()):
        raise ValueError("sandbox probe incomplete or rejected")


def check_graph_case(folder):
    paths = list(folder.rglob("*"))
    if any(path.is_symlink() for path in paths):
        raise ValueError("Graph case symlink")
    actual = {path.relative_to(folder).as_posix() for path in paths if path.is_file()}
    if not {"case.json", "README.md", "artifact-manifest.json"} <= actual:
        raise ValueError("Graph case chain files missing")
    case = json.loads((folder / "case.json").read_text())
    if case["kind"] != "graph_case" or case["case_id"] != folder.name or case["synthetic"] is not True:
        raise ValueError("invalid Graph case identity")
    graph_path = local_file(ROOT, case["graph"])
    if graph_path.parent != ROOT / "graphs" or graph_path.suffix != ".json":
        raise ValueError("invalid Graph catalog reference")
    graph = json.loads(graph_path.read_text())
    if (graph["kind"] != "graph_definition" or graph["max_parallel"] != 2
            or [n["id"] for n in graph["nodes"]] != ["title", "tags", "integration"]
            or [n["depends_on"] for n in graph["nodes"]] != [[], [], ["title", "tags"]]):
        raise ValueError("Graph fixture dependencies or limit drift")
    catalog_names = {case["graph"]}
    for node in graph["nodes"]:
        wf_path = local_file(ROOT, node["workflow"])
        if wf_path.parent != ROOT / "workflows" or wf_path.suffix != ".json":
            raise ValueError("invalid Workflow catalog path")
        wf = json.loads(wf_path.read_text())
        if wf["kind"] != "workflow_definition":
            raise ValueError("invalid Workflow definition kind")
        agent = local_file(ROOT, wf["agent"])
        if agent.parent != ROOT / "agents" or agent.suffix != ".md":
            raise ValueError("Workflow Agent reference invalid")
        catalog_names.update([node["workflow"], wf["agent"], *wf["skills"]])
        for name in wf["skills"]:
            skill = local_file(ROOT, name)
            if not skill.is_relative_to(ROOT / "skills") or skill.name != "SKILL.md":
                raise ValueError("Workflow Skill reference invalid")
    runtime = json.loads(local_file(folder, case["runtime_evidence"]).read_text())
    tests = json.loads(local_file(folder, case["tests_evidence"]).read_text())
    if runtime["synthetic"] is not True or runtime["status"] != "PASSED":
        raise ValueError("Graph receipt is not accepted")
    names = {"tools/execution/runtime.py", "tools/execution/catalog.py", "tools/execution/__init__.py",
             "scripts/run_graph.py", "tests/test_execution.py", case["graph"],
             "examples/concurrent-java-graph/run.py"}
    names.update(node["workflow"] for node in graph["nodes"])
    names.update(path.relative_to(ROOT).as_posix() for path in sorted((folder / "seed").glob("*.java")))
    sources = source_map(names)
    if runtime["source_sha256"] != sources or runtime["source_id"] != identity(sources):
        raise ValueError("Graph execution source drift")
    catalog = source_map(catalog_names)
    if runtime["catalog"]["source_sha256"] != catalog or runtime["catalog"]["catalog_id"] != identity(catalog):
        raise ValueError("Graph/Workflow/Agent/Skill catalog drift")
    if (runtime["graph_id"] != graph["graph_id"] or runtime["max_parallel"] != 2
            or runtime["host_capacity"] != 2 or runtime["peak_parallel"] != 2
            or runtime["instance_count"] != 4 or runtime["java_checks"] != 8):
        raise ValueError("Graph instance/capacity/Java result mismatch")
    for key in ["independent_workflows_overlap", "integration_waited", "merged_both_commits",
                "source_head_unchanged", "resources_removed"]:
        if runtime[key] is not True:
            raise ValueError("Graph execution or cleanup condition not confirmed")
    probe(runtime["graph_probe"])
    if set(runtime["nodes"]) != {"title", "tags", "integration"}:
        raise ValueError("Graph result nodes mismatch")
    workspaces = set()
    for name, item in runtime["nodes"].items():
        run_id = graph["graph_id"] + "/" + name
        if (item["run_id"] != run_id or item["parent_run_id"] != graph["graph_id"]
                or item["branch"] != "execution/" + run_id or item["status"] != "SUCCEEDED"
                or item["exit"] != 0 or item["success"] is not True or item["reason"] is not None):
            raise ValueError("Workflow instance result mismatch")
        probe(item["probe"])
        for key in ["input_commit", "commit"]:
            if not re.fullmatch(r"[0-9a-f]{40}", item[key]):
                raise ValueError("missing synthetic commit identity")
        for key in ["workspace_id", "log_sha256"]:
            if not re.fullmatch(r"[0-9a-f]{64}", item[key]):
                raise ValueError("missing workspace/log identity")
        workspaces.add(item["workspace_id"])
    if len(workspaces) != 3 or any(runtime["nodes"][n]["input_commit"] != runtime["base_commit"] for n in ["title", "tags"]):
        raise ValueError("shared base or independent workspaces mismatch")
    if runtime["nodes"]["integration"]["input_commit"] != runtime["nodes"]["integration"]["commit"]:
        raise ValueError("read-only merged validation candidate changed")
    if tests["source_id"] != runtime["source_id"] or tests["source_sha256"] != sources:
        raise ValueError("regression and Graph execution source receipts differ")
    module = ast.parse(local_file(ROOT, "tests/test_execution.py").read_text())
    expected_tests = sorted(c.name + "." + f.name for c in module.body if isinstance(c, ast.ClassDef)
                            for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test_"))
    if (tests["synthetic"] is not True or tests["platform"] != "Darwin" or tests["status"] != "PASSED"
            or tests["tests_run"] != 26 or len(expected_tests) != 26
            or sorted(tests["test_names"]) != expected_tests
            or tests["failures"] or tests["errors"] or tests["skipped"]):
        raise ValueError("regression receipt incomplete or source test names drifted")
    if case["verification"] != {"platform": "Darwin", "sandbox": "experimental_macos_foreground_seatbelt",
                                "native_agent": "not_run", "spring": "not_run"}:
        raise ValueError("Graph runtime scope mismatch")
    ids = []
    for row in case["acceptance"]:
        if not row["id"] or not row["expected"].strip():
            raise ValueError("empty Graph acceptance declaration")
        ids.append(row["id"]); local_file(folder, row["evidence"])
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Graph acceptance identity missing or duplicated")
    manifest = json.loads((folder / "artifact-manifest.json").read_text())["files"]
    if {row["path"] for row in manifest} != actual - {"artifact-manifest.json"} or len(manifest) != len(actual)-1:
        raise ValueError("Graph case manifest set drift")
    for row in manifest:
        if hashlib.sha256(local_file(folder, row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Graph case SHA drift")


def main():
    count = 0
    roles = runpy.run_path(str(ROOT / "scripts/check_agent_cases.py"))
    workflows = runpy.run_path(str(ROOT / "scripts/check_workflow_cases.py"))
    build = runpy.run_path(str(ROOT / "scripts/check_spring_build_cases.py"))
    for folder in sorted((ROOT / "examples").iterdir()):
        if not folder.is_dir():
            continue
        if folder.name == "bookmark-title":
            if (folder / "case.json").exists():
                raise ValueError("unexpected legacy Java case kind")
            continue
        case = json.loads(local_file(folder, "case.json").read_text())
        kind = case.get("kind", "role_case" if "agent" in case and "skill" in case else None)
        if kind == "graph_case":
            check_graph_case(folder); count += 1
        elif kind == "workflow_case":
            workflows["check_workflow_case"](folder)
        elif kind == "role_case":
            roles["check_case"](folder)
        elif kind == "spring_build_graph_case":
            build["check_spring_build_case"](folder)
        else:
            raise ValueError("unknown example kind")
    print(f"PASS: {count} Graph cases; declarations, source/catalog identity and recorded result consistency only")


if __name__ == "__main__":
    main()
