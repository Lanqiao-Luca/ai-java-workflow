"""Actual isolated Graph/Workflow Java demonstration, using synthetic temporary Git data."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
CASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools.execution.catalog import load_definition
from tools.execution.runtime import GraphRun, Rejected, git, identity


def execution_sources():
    names = ["tools/execution/runtime.py", "tools/execution/catalog.py", "tools/execution/__init__.py",
             "scripts/run_graph.py", "tests/test_execution.py", "graphs/concurrent-java.json",
             "workflows/concurrent-java-title.json", "workflows/concurrent-java-tags.json",
             "workflows/concurrent-java-integration.json", "examples/concurrent-java-graph/run.py"]
    names += [p.relative_to(ROOT).as_posix() for p in sorted((CASE / "seed").glob("*.java"))]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
    return {"source_id": identity(hashes), "source_sha256": hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and (args.output.resolve().is_relative_to(CASE) or args.output.exists()):
        raise SystemExit("Refusing to overwrite case or existing output evidence")
    if platform.system() != "Darwin":
        print("NOT_RUN: only the experimental macOS foreground backend is implemented"); return 2
    if not (args.java_home / "bin/java").is_file():
        print("NOT_RUN: explicit usable JDK17+ home required"); return 2
    rows = json.loads((CASE / "artifact-manifest.json").read_text())["files"]
    actual = {p.relative_to(CASE).as_posix() for p in CASE.rglob("*") if p.is_file()}
    if {row["path"] for row in rows} != actual - {"artifact-manifest.json"} or len(rows) != len(actual)-1:
        raise SystemExit("FAIL: case file set drift")
    for row in rows:
        path = (CASE / row["path"]).resolve()
        if not path.is_relative_to(CASE) or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise SystemExit("FAIL: case identity drift")
    definition, catalog = load_definition(ROOT / "graphs/concurrent-java.json", ROOT)
    report = {"synthetic": True, **execution_sources(), "catalog": catalog,
              "scope": "Real worktrees, probed Seatbelt foreground commands, two Java feature Workflows and merged validation"}
    with tempfile.TemporaryDirectory(prefix="concurrent-java-") as temporary:
        area = Path(temporary).resolve(); seed = area / "seed"; seed.mkdir()
        for file in (CASE / "seed").glob("*.java"): shutil.copyfile(file, seed / file.name)
        git(seed, "init", "--initial-branch=main"); git(seed, "add", "--all"); git(seed, "commit", "-m", "Independent synthetic Java seed")
        base = git(seed, "rev-parse", "HEAD").stdout.strip()
        run = GraphRun(seed, base, area / "runtime", definition, tool_roots=[args.java_home],
                       java_home=args.java_home, host_capacity=2)
        try:
            state = run.run()
            if state["status"] != "SUCCEEDED":
                print("FAILED: Graph did not satisfy its Workflow contracts"); return 1
            a, b, joined = [state["nodes"][n] for n in ["title", "tags", "integration"]]
            overlap = a["started_at"] < b["ended_at"] and b["started_at"] < a["ended_at"]
            dependency = joined["started_at"] >= max(a["ended_at"], b["ended_at"])
            parents = [git(run.resources["integration"] / "worktree", "merge-base", "--is-ancestor", state["nodes"][n]["commit"], joined["input_commit"], check=False).returncode == 0 for n in ["title", "tags"]]
            if not overlap or not dependency or not all(parents):
                print("FAILED: overlap, dependency or candidate ancestry did not hold"); return 1
            if git(seed, "rev-parse", "HEAD").stdout.strip() != base:
                print("FAILED: source HEAD changed"); return 1
            retained = run.cleanup()
            if retained: print("FAILED: unexpected dirty resources retained"); return 1
            report.update(status="PASSED", base_commit=base, graph_id=state["graph_id"],
                          max_parallel=2, host_capacity=2, peak_parallel=state["peak_parallel"],
                          independent_workflows_overlap=overlap, integration_waited=dependency,
                          merged_both_commits=all(parents), source_head_unchanged=True,
                          resources_removed=state["cleanup"] == "worktrees_removed", instance_count=4,
                          java_checks=8, nodes={n: {k: v for k, v in item.items() if k in {
                              "status", "run_id", "parent_run_id", "branch", "probe", "input_commit", "commit",
                              "exit", "reason", "success", "workspace_id", "log_sha256"}}
                              for n, item in state["nodes"].items()}, graph_probe=state["graph_resource"]["probe"])
        finally:
            run.close()
    if args.output: args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: real concurrent Java Graph; 4 isolated instances, 2 parallel features, merged 8 checks, safe cleanup")
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except Rejected:
        print("REJECTED: sandbox/snapshot admission failed; no bare-process fallback")
        raise SystemExit(2)
