"""Passive trusted-build case, source and result consistency; no builds/downloads."""
from pathlib import Path
import ast
import hashlib
import json
import re
import runpy
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PROBES = {"positive_write", "child_exec_succeeded", "child_outside_read_denied",
          "child_outside_write_denied", "child_admin_read_denied", "child_admin_write_denied",
          "child_external_network_denied", "own_loopback_ipc_succeeded", "observed_tree_stopped"}


def local(base, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("invalid relative reference")
    path = (base / value).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise ValueError("missing or outside-scope file")
    return path


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def hashes(names):
    return {name: hashlib.sha256(local(ROOT, name).read_bytes()).hexdigest() for name in names}


def test_names(path):
    module = ast.parse(path.read_text())
    return sorted(c.name + "." + f.name for c in module.body if isinstance(c, ast.ClassDef)
                  for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test_"))


def check_regression(report, expected, count):
    if (report["synthetic"] is not True or report["status"] != "PASSED"
            or report["tests_run"] != count or len(expected) != count
            or sorted(report["test_names"]) != expected or report["failures"]
            or report["errors"] or report["skipped"]):
        raise ValueError("regression receipt inconsistent")


def check_probe(value):
    if set(value) != PROBES or any(x is not True for x in value.values()):
        raise ValueError("inherited trusted-build sandbox probe incomplete")


def check_spring_build_case(folder):
    paths = list(folder.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("case symlink")
    actual = {p.relative_to(folder).as_posix() for p in paths if p.is_file()}
    if not {"README.md", "case.json", "artifact-manifest.json"} <= actual:
        raise ValueError("missing case declarations")
    case = json.loads((folder / "case.json").read_text())
    if case["kind"] != "spring_build_graph_case" or case["case_id"] != folder.name or case["synthetic"] is not True:
        raise ValueError("wrong case kind/identity")
    graph_path = local(ROOT, case["graph"])
    if graph_path.parent != ROOT / "graphs" or graph_path.suffix != ".json":
        raise ValueError("invalid Graph reference")
    graph = json.loads(graph_path.read_text())
    if (graph["kind"] != "graph_definition" or graph["graph_id"] != "spring-build"
            or graph["max_parallel"] != 2 or [n["id"] for n in graph["nodes"]] != ["title", "tags", "integration"]
            or [n["depends_on"] for n in graph["nodes"]] != [[], [], ["title", "tags"]]):
        raise ValueError("Graph fixture dependency/limit mismatch")
    catalog_names = {case["graph"]}
    for node in graph["nodes"]:
        wf_path = local(ROOT, node["workflow"])
        if wf_path.parent != ROOT / "workflows" or wf_path.suffix != ".json":
            raise ValueError("invalid Workflow reference")
        wf = json.loads(wf_path.read_text())
        if wf["kind"] != "workflow_definition" or wf["agent"] != "agents/java-build-executor.md":
            raise ValueError("build Workflow role mismatch")
        local(ROOT, wf["agent"])
        for name in wf["skills"]:
            if not local(ROOT, name).is_relative_to(ROOT / "skills"):
                raise ValueError("build Skill outside supported catalog")
        catalog_names.update([node["workflow"], wf["agent"], *wf["skills"]])
    reports = {key: json.loads(local(folder, case[key + "_evidence"]).read_text())
               for key in ["runtime", "tests", "negative", "legacy", "toolchain"]}
    runtime = reports["runtime"]
    names = {"tools/execution/runtime.py", "tools/execution/catalog.py", "tools/execution/build_runtime.py",
             "tools/execution/build_cache.py", "scripts/run_build_graph.py", "tests/test_build_execution.py",
             "standards/java-build-sandbox.md", "examples/spring-build-graph/run.py",
             "examples/spring-build-graph/prepare.py", "examples/spring-build-graph/negative.py"} | catalog_names
    names.update(p.relative_to(ROOT).as_posix() for p in (folder / "seed").rglob("*") if p.is_file())
    sources = hashes(names)
    for key in ["runtime", "tests", "negative"]:
        item = reports[key]
        if (item["synthetic"] is not True or item["status"] != "PASSED"
                or item["source_sha256"] != sources or item["source_id"] != identity(sources)):
            raise ValueError("build source/receipt identity drift")
    catalog = hashes(catalog_names)
    if runtime["catalog"] != {"catalog_id": identity(catalog), "source_sha256": catalog}:
        raise ValueError("build catalog identity drift")
    if (runtime["kind"] != "spring_build_graph_receipt" or runtime["platform"] != "Darwin"
            or runtime["mode"] != "trusted_macos_build_tree" or runtime["instance_count"] != 4
            or runtime["max_parallel"] != 2 or runtime["host_capacity"] != 2 or runtime["peak_parallel"] != 2):
        raise ValueError("build execution scope/capacity mismatch")
    for key in ["independent_workflows_overlap", "integration_waited", "merged_both_commits", "source_head_unchanged", "resources_removed"]:
        if runtime[key] is not True:
            raise ValueError("build integration/cleanup condition missing")
    check_probe(runtime["graph_probe"])
    if set(runtime["nodes"]) != {"title", "tags", "integration"}:
        raise ValueError("build node set mismatch")
    workspaces = set()
    for name, item in runtime["nodes"].items():
        run_id = "spring-build/" + name
        if (item["run_id"] != run_id or item["parent_run_id"] != "spring-build"
                or item["branch"] != "execution/" + run_id or item["status"] != "SUCCEEDED"
                or item["exit"] != 0 or item["reason"] is not None or item["success"] is not True
                or item["tree_stopped"] is not True or item["child_seen"] is not True
                or item["allow_observed_daemon"] is not True or item["observed_process_peak"] < 2):
            raise ValueError("build job/tree result inconsistent")
        check_probe(item["probe"])
        for key in ["input_commit", "commit"]:
            if not re.fullmatch(r"[0-9a-f]{40}", item[key]):
                raise ValueError("missing synthetic candidate")
        for key in ["workspace_id", "log_sha256"]:
            if not re.fullmatch(r"[0-9a-f]{64}", item[key]):
                raise ValueError("missing build workspace/log identity")
        workspaces.add(item["workspace_id"])
    if len(workspaces) != 3 or any(runtime["nodes"][n]["input_commit"] != runtime["base_commit"] for n in ["title", "tags"]):
        raise ValueError("build workspaces or base mismatch")
    if runtime["nodes"]["integration"]["input_commit"] != runtime["nodes"]["integration"]["commit"]:
        raise ValueError("integrated read-only build candidate changed")
    if set(runtime["cache_ids"]) != {"maven", "gradle"} or any(not re.fullmatch(r"[0-9a-f]{64}", h) for h in runtime["cache_ids"].values()):
        raise ValueError("missing sealed cache identities")
    matrix = {"title": {"maven": (3, ["example.graph.TitleApiTest"])},
              "tags": {"gradle": (3, ["example.graph.TagsApiTest"])},
              "integration": {tool: (8, ["example.graph.IntegrationTest", "example.graph.TagsApiTest", "example.graph.TitleApiTest"])
                              for tool in ["maven", "gradle"]}}
    if set(runtime["builds"]) != set(matrix):
        raise ValueError("build matrix mismatch")
    for node, tools in matrix.items():
        if set(runtime["builds"][node]) != set(tools):
            raise ValueError("tool result set mismatch")
        for tool, (count, suites) in tools.items():
            item = runtime["builds"][node][tool]
            if (item["tool"] != tool or item["tests"] != count or item["failures"] or item["errors"]
                    or item["skipped"] or sorted(item["suites"]) != suites or item["distinct_test_jvm"] is not True):
                raise ValueError("JUnit/tool/test-JVM receipt inconsistent")
            if len(item["artifacts"]) != 1:
                raise ValueError("expected one packaged Boot artifact")
            artifact = item["artifacts"][0]
            if (artifact["boot_jar"] is not True or not artifact["name"].endswith(".jar")
                    or "/" in artifact["name"] or artifact["bytes"] <= 0
                    or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"])):
                raise ValueError("packaging identity missing; not a deployment assertion")
    check_regression(reports["tests"], test_names(local(ROOT, "tests/test_build_execution.py")), 12)
    check_regression(reports["legacy"], test_names(local(ROOT, "tests/test_execution.py")), 26)
    for key, name in [("runtime_sha256", "tools/execution/runtime.py"), ("test_source_sha256", "tests/test_execution.py")]:
        if reports["legacy"][key] != hashlib.sha256(local(ROOT, name).read_bytes()).hexdigest():
            raise ValueError("strict legacy source drift")
    controls = reports["negative"]["controls"]
    if set(controls) != {"red_baseline", "missing_dependency"}:
        raise ValueError("negative controls missing")
    for key, item in controls.items():
        if (item["status"] != "EXPECTED_FAILURE" or item["exit"] != 1 or item["candidate_promoted"] is not False
                or item["dependent"] != "BLOCKED" or item["tree_stopped"] is not True or item["source_head_unchanged"] is not True):
            raise ValueError("failed build promoted or dependent unblocked")
    if controls["red_baseline"]["junit"] != {"tests": 3, "failures": 2, "errors": 0, "skipped": 0} or controls["missing_dependency"]["offline_dependency_failure"] is not True:
        raise ValueError("real failure shape mismatch")
    toolchain = reports["toolchain"]
    if toolchain["distribution_checksums"] != "VERIFIED" or toolchain["spring_boot"] != "3.5.16":
        raise ValueError("toolchain provenance declaration incomplete")
    if {t["name"] for t in toolchain["tools"]} != {"Temurin JDK", "Apache Maven", "Gradle"}:
        raise ValueError("missing public toolchain declarations")
    for item in toolchain["tools"]:
        length = 64 if item["algorithm"] == "SHA256" else 128 if item["algorithm"] == "SHA512" else 0
        if not length or not re.fullmatch(r"[0-9a-f]{" + str(length) + r"}", item["digest"]):
            raise ValueError("tool distribution digest invalid")
        if urlsplit(item["source"]).hostname not in {"github.com", "repo.maven.apache.org", "downloads.gradle.org"}:
            raise ValueError("unreviewed distribution host")
    if case["verification"] != {"platform": "Darwin", "sandbox": "trusted_macos_build_tree",
                                "single_use_daemon": "explicit_observed_opt_in", "external_network": "denied",
                                "loopback": "allowed_broad", "native_agent": "not_run", "deployment": "not_run"}:
        raise ValueError("trusted-build scope declaration mismatch")
    ids = []
    for row in case["acceptance"]:
        if not row["id"] or not row["expected"].strip(): raise ValueError("empty acceptance")
        ids.append(row["id"]); local(folder, row["evidence"])
    if not ids or len(ids) != len(set(ids)): raise ValueError("acceptance IDs invalid")
    manifest = json.loads((folder / "artifact-manifest.json").read_text())["files"]
    if {r["path"] for r in manifest} != actual - {"artifact-manifest.json"} or len(manifest) != len(actual)-1:
        raise ValueError("case manifest set drift")
    for row in manifest:
        if hashlib.sha256(local(folder, row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("case SHA drift")


def main():
    count = 0
    role = runpy.run_path(str(ROOT / "scripts/check_agent_cases.py"))
    workflow = runpy.run_path(str(ROOT / "scripts/check_workflow_cases.py"))
    graph = runpy.run_path(str(ROOT / "scripts/check_graph_cases.py"))
    for folder in sorted((ROOT / "examples").iterdir()):
        if not folder.is_dir(): continue
        if folder.name == "bookmark-title":
            if (folder / "case.json").exists(): raise ValueError("legacy Java type mismatch")
            continue
        case = json.loads(local(folder, "case.json").read_text())
        kind = case.get("kind", "role_case" if "agent" in case and "skill" in case else None)
        if kind == "spring_build_graph_case": check_spring_build_case(folder); count += 1
        elif kind == "graph_case": graph["check_graph_case"](folder)
        elif kind == "workflow_case": workflow["check_workflow_case"](folder)
        elif kind == "role_case": role["check_case"](folder)
        else: raise ValueError("unknown example kind")
    print(f"PASS: {count} Spring build Graph cases; source/catalog, declared results, failure controls and identities only; no builds executed")


if __name__ == "__main__":
    main()
