"""Passive Docker case identity and receipt consistency, without Docker or builds."""
from pathlib import Path
import ast
import hashlib
import json
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]
PROBES = {"capabilities_dropped", "cpu_cgroup_limit", "docker_socket_absent", "external_network_denied",
          "fork_and_setsid_succeeded", "git_pointer_absent", "host_file_absent", "host_loopback_isolated",
          "memory_cgroup_limit", "namespace_drained", "no_new_privileges", "non_root", "only_loopback_interface",
          "own_loopback_ipc", "pids_cgroup_limit", "readonly_root", "seccomp_filter", "workspace_write"}


def local(base, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("invalid relative path")
    p = (base / name).resolve()
    if not p.is_relative_to(base.resolve()) or not p.is_file():
        raise ValueError("missing or outside-scope file")
    return p


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def hashes(names):
    return {n: hashlib.sha256(local(ROOT, n).read_bytes()).hexdigest() for n in names}


def test_names(name):
    tree = ast.parse(local(ROOT, name).read_text())
    return sorted(c.name + "." + f.name for c in tree.body if isinstance(c, ast.ClassDef)
                  for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test_"))


def probe(value):
    if set(value) != PROBES or any(x is not True for x in value.values()):
        raise ValueError("Docker real probe incomplete")


def check_docker_case(folder):
    paths = list(folder.rglob("*"))
    if any(p.is_symlink() for p in paths): raise ValueError("case symlink")
    actual = {p.relative_to(folder).as_posix() for p in paths if p.is_file()}
    case = json.loads(local(folder, "case.json").read_text())
    if (case["kind"] != "docker_spring_graph_case" or case["case_id"] != folder.name
            or case["synthetic"] is not True or case["base_case"] != "examples/spring-build-graph"):
        raise ValueError("Docker case identity mismatch")
    graph = json.loads(local(ROOT, case["graph"]).read_text())
    if (case["graph"] != "graphs/docker-spring.json" or graph["kind"] != "graph_definition"
            or graph["graph_id"] != "docker-spring" or graph["max_parallel"] != 2
            or [n["id"] for n in graph["nodes"]] != ["title", "tags", "integration"]
            or [n["depends_on"] for n in graph["nodes"]] != [[], [], ["title", "tags"]]):
        raise ValueError("Docker Graph dependency/limit mismatch")
    catalog_names = {case["graph"]}
    for node in graph["nodes"]:
        wf = json.loads(local(ROOT, node["workflow"]).read_text())
        if wf["kind"] != "workflow_definition" or wf["agent"] != "agents/container-build-executor.md":
            raise ValueError("Docker Workflow role mismatch")
        if set(wf["skills"]) != {"skills/code-implementation/SKILL.md", "skills/docker-build-isolation/SKILL.md"}:
            raise ValueError("Docker method consumption mismatch")
        catalog_names.update([node["workflow"], wf["agent"], *wf["skills"]])
    names = {"tools/execution/runtime.py", "tools/execution/catalog.py", "tools/execution/build_fixture.py",
             "tools/execution/build_runtime.py", "tools/execution/build_cache.py", "tools/execution/docker_io.py",
             "tools/execution/docker_runtime.py", "tools/docker/worker.py", "tools/docker/prewarm.py",
             "tools/docker/Dockerfile", "scripts/run_docker_graph.py", "examples/docker-spring-graph/run.py",
             "examples/docker-spring-graph/build.py", "examples/docker-spring-graph/negative.py",
             "tests/test_docker_io.py", "tests/test_docker_backend.py"} | catalog_names
    seed = ROOT / case["base_case"] / "seed"
    names.update(p.relative_to(ROOT).as_posix() for p in seed.rglob("*") if p.is_file())
    names.update(p.relative_to(ROOT).as_posix() for p in (folder / "overlay").rglob("*") if p.is_file())
    sources = hashes(names); catalog = hashes(catalog_names)
    def bound(report):
        if (report["synthetic"] is not True or report["status"] != "PASSED"
                or report["source_sha256"] != sources or report["source_id"] != identity(sources)):
            raise ValueError("Docker source/receipt drift")
    def read(key): return json.loads(local(folder, case[key + "_evidence"]).read_text())
    tests, image, environment, resources = [read(k) for k in ["tests", "image", "environment", "resource"]]
    bound(tests)
    if (image["synthetic"] is not True or image["status"] != "PASSED" or image["container_os"] != "linux"
            or image["image_arch"] != "arm64" or not re.fullmatch(r"sha256:[0-9a-f]{64}", image["image_id"])
            or not re.fullmatch(r"eclipse-temurin@sha256:[0-9a-f]{64}", image["base_image"])
            or image["image_pushed"] is not False or image["dependency_preparation"] != "online_public_central"):
        raise ValueError("local immutable image scope mismatch")
    if (tests["image_id"] != image["image_id"] or not tests["image_id_provenance"].strip()
            or tests["image_id_scope"] != "Real Engine regressions only; IO unit tests do not invoke containers."):
        raise ValueError("regression image/scope/provenance mismatch")
    context = {p.relative_to(seed).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in seed.rglob("*") if p.is_file()}
    context = {"seed/" + k: v for k, v in context.items()}
    context.update({n: hashlib.sha256(local(ROOT, "tools/docker/" + n).read_bytes()).hexdigest()
                    for n in ["Dockerfile", "worker.py", "prewarm.py"]})
    recorded = image["context_sha256"]
    if (set(recorded) != set(context) | {"maven.tar.gz", "gradle.zip"}
            or any(recorded[k] != v for k, v in context.items())
            or any(not re.fullmatch(r"[0-9a-f]{64}", v) for v in recorded.values())
            or image["context_id"] != identity(recorded)):
        raise ValueError("image context whitelist/source identity drift")
    if (environment["synthetic"] is not True or environment["status"] != "RECORDED"
            or environment["architecture_tested"] != "arm64" or environment["engine_os"] != "Linux"
            or environment["cgroup_version"] != "2" or set(environment["hosts"]) != {"Darwin", "Linux"}
            or environment["owned_test_vm_stopped_after_validation"] is not True):
        raise ValueError("actual host/Engine/VM boundary missing")
    if resources["status"] != "PASSED" or resources["remaining_sdk_containers"] != 0 or resources["remaining_sdk_volumes"] != 0:
        raise ValueError("owned resources remain")
    if set(tests["hosts"]) != {"Darwin", "Linux"}: raise ValueError("dual-host tests missing")
    for host in ["Darwin", "Linux"]:
        for kind, name, count in [("kernel", "tests/test_docker_backend.py", 13), ("io", "tests/test_docker_io.py", 8)]:
            report = tests["hosts"][host][kind]; expected = test_names(name)
            if (report["status"] != "PASSED" or report["tests_run"] != count or len(expected) != count
                    or sorted(report["test_names"]) != expected or report["failures"] or report["errors"] or report["skipped"]):
                raise ValueError("Docker test AST/receipt mismatch")
        injected = tests["hosts"][host]["injected_controls"]
        if set(injected) != {"DockerKernelTests.test_closed_owner_refuses_docker_cleanup",
                             "DockerKernelTests.test_control_plane_failure_retains_active_pool_and_outputs"}:
            raise ValueError("host fault-injection disclosure mismatch")
    if set(case["runtime_evidence"]) != {"Darwin", "Linux"} or set(case["negative_evidence"]) != {"Darwin", "Linux"}:
        raise ValueError("dual-host execution missing")
    matrix = {"title": {"maven": (3, ["example.graph.TitleApiTest"])},
              "tags": {"gradle": (3, ["example.graph.TagsApiTest"])},
              "integration": {t: (8, ["example.graph.IntegrationTest", "example.graph.TagsApiTest", "example.graph.TitleApiTest"])
                              for t in ["maven", "gradle"]}}
    for host, name in case["runtime_evidence"].items():
        runtime = json.loads(local(folder, name).read_text()); bound(runtime)
        if (runtime["kind"] != "docker_spring_graph_receipt" or runtime["host_os"] != host
                or runtime["host_description"] != {"Darwin": "macos-vm-engine", "Linux": "linux-vm-engine"}[host]
                or runtime["container_os"] != "linux" or runtime["image_id"] != image["image_id"]
                or runtime["image_arch"] != "arm64" or runtime["catalog"] != {"catalog_id": identity(catalog), "source_sha256": catalog}
                or runtime["instance_count"] != 4 or runtime["max_parallel"] != 2
                or runtime["host_capacity"] != 2 or runtime["peak_parallel"] != 2):
            raise ValueError("host/image/catalog/capacity drift")
        for k in ["build_commands_overlap", "independent_workflows_overlap", "integration_waited", "merged_both_commits",
                  "source_head_unchanged", "resources_removed", "all_owned_containers_and_volumes_removed"]:
            if runtime[k] is not True: raise ValueError("execution overlap/merge/cleanup incomplete")
        probe(runtime["graph_probe"])
        if set(runtime["nodes"]) != set(matrix) or set(runtime["builds"]) != set(matrix): raise ValueError("node set mismatch")
        ids = set(); bases = set()
        for node, item in runtime["nodes"].items():
            run_id = "docker-spring/" + node
            if (item["status"] != "SUCCEEDED" or item["run_id"] != run_id or item["parent_run_id"] != "docker-spring"
                    or item["branch"] != "execution/" + run_id or item["exit"] != 0 or item["reason"] is not None
                    or item["success"] is not True or item["tree_stopped"] is not True
                    or item["memory_limit"] != 2147483648 or item["cpu_limit"] != 2 or item["pids_limit"] != 256):
                raise ValueError("node completion/resource mismatch")
            probe(item["probe"])
            for k in ["input_commit", "commit"]:
                if not re.fullmatch(r"[0-9a-f]{40}", item[k]): raise ValueError("candidate commit missing")
            for k in ["workspace_id", "log_sha256"]:
                if not re.fullmatch(r"[0-9a-f]{64}", item[k]): raise ValueError("workspace/log identity missing")
            ids.add(item["workspace_id"])
            if node != "integration": bases.add(item["input_commit"])
            elif item["input_commit"] != item["commit"]: raise ValueError("read-only integration drift")
            if set(runtime["builds"][node]) != set(matrix[node]): raise ValueError("build tool matrix mismatch")
            for tool, (count, suites) in matrix[node].items():
                b = runtime["builds"][node][tool]
                if (b["tool"] != tool or b["tests"] != count or b["failures"] or b["errors"] or b["skipped"]
                        or sorted(b["suites"]) != suites or b["distinct_test_jvm"] is not True or len(b["artifacts"]) != 1):
                    raise ValueError("JUnit/tool/test-JVM mismatch")
                a = b["artifacts"][0]
                if (a["boot_jar"] is not True or a["bytes"] <= 0 or "/" in a["name"] or not a["name"].endswith(".jar")
                        or not re.fullmatch(r"[0-9a-f]{64}", a["sha256"])): raise ValueError("Boot JAR summary incomplete")
        if len(ids) != 3 or len(bases) != 1: raise ValueError("workspace or frozen base mismatch")
        negative = json.loads(local(folder, case["negative_evidence"][host]).read_text()); bound(negative)
        if negative["image_id"] != image["image_id"] or not negative["image_id_provenance"].strip():
            raise ValueError("negative image/provenance mismatch")
        if negative["host_os"] != host or set(negative["controls"]) != {"red_baseline", "missing_dependency"}:
            raise ValueError("negative host/control mismatch")
        for n in negative["controls"].values():
            if (n["status"] != "EXPECTED_FAILURE" or n["exit"] != 1 or n["dependent"] != "BLOCKED"
                    or n["candidate_promoted"] is not False or n["tree_stopped"] is not True
                    or n["source_head_unchanged"] is not True or n["known_synthetic_outputs_explicitly_removed"] is not True):
                raise ValueError("failed candidate promoted or unknown output removed")
        if (negative["controls"]["red_baseline"]["junit"] != {"tests": 3, "failures": 2, "errors": 0, "skipped": 0}
                or negative["controls"]["missing_dependency"]["offline_dependency_failure"] is not True):
            raise ValueError("negative build failure shape mismatch")
    if case["verification"] != {"host_os": ["Darwin", "Linux"], "container_os": "linux",
        "engine": "explicit_local_unix_cgroup_v2", "linux_host": "owned_vm_guest", "architectures_tested": ["arm64"],
        "native_agent": "not_run", "application_start": "not_run", "deployment": "not_run"}:
        raise ValueError("actual support boundary mismatch")
    ids = []
    for row in case["acceptance"]:
        if not row["id"] or not row["expected"].strip(): raise ValueError("acceptance empty")
        ids.append(row["id"]); local(folder, row["evidence"])
    if not ids or len(ids) != len(set(ids)): raise ValueError("acceptance identity mismatch")
    rows = json.loads(local(folder, "artifact-manifest.json").read_text())["files"]
    if {x["path"] for x in rows} != actual - {"artifact-manifest.json"} or len(rows) != len(actual)-1:
        raise ValueError("Docker case manifest set mismatch")
    for row in rows:
        if hashlib.sha256(local(folder, row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Docker case byte drift")


def main():
    modules = {"role_case": ("check_agent_cases.py", "check_case"),
               "workflow_case": ("check_workflow_cases.py", "check_workflow_case"),
               "graph_case": ("check_graph_cases.py", "check_graph_case"),
               "spring_build_graph_case": ("check_spring_build_cases.py", "check_spring_build_case")}
    checks = {k: runpy.run_path(str(ROOT / "scripts" / f))[fn] for k, (f, fn) in modules.items()}
    checks["docker_spring_graph_case"] = check_docker_case; count = 0
    for folder in sorted((ROOT / "examples").iterdir()):
        if not folder.is_dir(): continue
        if folder.name == "bookmark-title":
            if (folder / "case.json").exists(): raise ValueError("legacy Java kind mismatch")
            continue
        case = json.loads(local(folder, "case.json").read_text())
        kind = case.get("kind", "role_case" if "agent" in case and "skill" in case else None)
        if kind not in checks: raise ValueError("unknown example kind")
        checks[kind](folder)
        if kind == "docker_spring_graph_case": count += 1
    print(f"PASS: {count} Docker Spring Graph cases; source/catalog/image/context/dual-host receipt consistency only; no Docker/build execution")


if __name__ == "__main__":
    main()
