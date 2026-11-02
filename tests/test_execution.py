"""Real Git + macOS Seatbelt regressions using only synthetic temporary repositories."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
import platform
import runpy
import sys
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from tools.execution import runtime as runtime_module
from tools.execution.catalog import load_definition
R = vars(runtime_module)
GraphRun, Rejected, git = R["GraphRun"], R["Rejected"], R["git"]

WORKER = '''import pathlib,subprocess,sys,time
mode=sys.argv[1]
if mode=="sleep":
 time.sleep(30)
elif mode in {"fork","detached"}:
 try:
  child=subprocess.Popen([sys.executable,"-I","-B","-c","import time;time.sleep(0.2)"],start_new_session=mode=="detached")
  child.wait()
  raise RuntimeError("subprocess should be denied")
 except PermissionError:
  print("FORK_DENIED")
  raise SystemExit(0)
elif mode=="fail": raise SystemExit(3)
elif mode=="marker": print("not the required result"); raise SystemExit(0)
elif mode=="escape": pathlib.Path("not-allowed.txt").write_text("synthetic")
elif mode=="join":
 assert pathlib.Path("a.txt").read_text()=="a"
 assert pathlib.Path("b.txt").read_text()=="b"
else:
 time.sleep(0.4)
 target="shared.txt" if mode.startswith("conflict-") else mode+".txt"
 pathlib.Path(target).write_text(mode)
print("OK")
'''


def node(name, deps=(), mode=None, writes=None, timeout=5):
    return {"id": name, "depends_on": list(deps),
            "command": ["{python}", "-I", "-B", "worker.py", mode or name],
            "allowed_write": [name + ".txt"] if writes is None else writes,
            "success_pattern": "^OK$", "timeout": timeout}


class DefinitionTests(unittest.TestCase):
    def test_bad_dags_and_commands_rejected(self):
        good = {"graph_id": "unit", "max_parallel": 2, "nodes": [node("a")]}
        for change in [
            lambda x: x.update(max_parallel=0),
            lambda x: x["nodes"].append(copy.deepcopy(x["nodes"][0])),
            lambda x: x["nodes"][0].update(depends_on=["missing"]),
            lambda x: x["nodes"][0].update(depends_on=["a"]),
            lambda x: x["nodes"][0].update(command="echo unsafe shell string"),
            lambda x: x["nodes"][0].update(allowed_write=["../outside"]),
            lambda x: x["nodes"][0].update(success_pattern="^(a+)+$"),
            lambda x: x["nodes"][0].update(id="graph"),
        ]:
            value = copy.deepcopy(good); change(value)
            with self.subTest(value=value):
                with self.assertRaises(Rejected): R["validate"](value)

    def test_catalog_binds_workflow_and_rejects_escape(self):
        with tempfile.TemporaryDirectory(prefix="catalog-tests-") as d:
            root = Path(d).resolve()
            for name in ["graphs", "workflows", "agents", "skills/demo"]: (root/name).mkdir(parents=True)
            (root/"agents/demo.md").write_text("synthetic role")
            (root/"skills/demo/SKILL.md").write_text("synthetic skill")
            workflow = {"kind":"workflow_definition", "agent":"agents/demo.md", "skills":["skills/demo/SKILL.md"],
                        "command":["{python}","worker.py"],"allowed_write":[],"success_pattern":"^OK$","timeout":1}
            (root/"workflows/demo.json").write_text(json.dumps(workflow))
            graph = {"kind":"graph_definition","graph_id":"catalog","max_parallel":1,
                     "nodes":[{"id":"a","depends_on":[],"workflow":"workflows/demo.json"}]}
            file=root/"graphs/demo.json";file.write_text(json.dumps(graph))
            expanded, sources = load_definition(file,root)
            self.assertEqual(expanded["nodes"][0]["command"],["{python}","worker.py"])
            self.assertEqual(len(sources["source_sha256"]),4)
            graph["nodes"][0]["workflow"]="../outside.json";file.write_text(json.dumps(graph))
            with self.assertRaises(Rejected): load_definition(file,root)

    def test_unsupported_backend_is_fail_closed(self):
        with patch.object(platform, "system", return_value="Unsupported"):
            with self.assertRaisesRegex(Rejected, "UNSUPPORTED_SANDBOX"):
                R["Seatbelt"]()


@unittest.skipUnless(platform.system() == "Darwin" and Path("/usr/bin/sandbox-exec").exists(),
                     "actual Seatbelt regressions require macOS; no fallback is tested as sandbox")
class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="execution-tests-")
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "seed"; self.repo.mkdir()
        git(self.repo, "init", "--initial-branch=main")
        (self.repo / "worker.py").write_text(WORKER)
        (self.repo / "shared.txt").write_text("base")
        git(self.repo, "add", "worker.py", "shared.txt")
        git(self.repo, "commit", "-m", "Independently constructed seed")
        self.base = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.opened = []

    def tearDown(self):
        for run in self.opened:
            if not run.lock.closed: run.close()
        self.temp.cleanup()

    def make(self, nodes, limit=2, name="unit", root=None, host=None):
        graph = GraphRun(self.repo, self.base, root or self.root / "runs",
                         {"graph_id": name, "max_parallel": limit, "nodes": nodes}, host_capacity=host)
        self.opened.append(graph)
        return graph

    def test_real_parallel_isolation_dependency_and_cleanup(self):
        g = self.make([node("a"), node("b"), node("join", ["a", "b"], writes=[])])
        state = g.run()
        self.assertEqual(state["status"], "SUCCEEDED")
        a, b, joined = [state["nodes"][x] for x in ["a", "b", "join"]]
        self.assertLess(a["started_at"], b["ended_at"])
        self.assertLess(b["started_at"], a["ended_at"])
        self.assertGreaterEqual(joined["started_at"], max(a["ended_at"], b["ended_at"]))
        self.assertEqual(state["peak_parallel"], 2)
        for item in [a, b, joined, state["graph_resource"]]:
            self.assertTrue(all(item["probe"].values()))
        self.assertNotEqual(a["branch"], b["branch"])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD").stdout.strip(), self.base)
        self.assertEqual(g.cleanup(), [])
        self.assertEqual(g.cleanup(), [])
        for resource in g.resources.values():
            self.assertFalse((resource / "worktree").exists())
            self.assertFalse((resource / "sandbox/home").exists())
        with self.assertRaises(Rejected): g.run()

    def test_limit_one_serializes_actual_processes(self):
        state = self.make([node("a"), node("b")], limit=1).run()
        self.assertEqual(state["status"], "SUCCEEDED")
        self.assertEqual(state["peak_parallel"], 1)
        self.assertGreaterEqual(state["nodes"]["b"]["started_at"], state["nodes"]["a"]["ended_at"])

    def test_failure_blocks_descendant_but_not_independent(self):
        state = self.make([node("a", mode="fail"), node("b"), node("join", ["a"], writes=[])]).run()
        self.assertEqual(state["nodes"]["a"]["status"], "FAILED")
        self.assertEqual(state["nodes"]["b"]["status"], "SUCCEEDED")
        self.assertEqual(state["nodes"]["join"]["status"], "BLOCKED")

    def test_timeout_stops_group_and_does_not_promote(self):
        g = self.make([node("a", mode="sleep", timeout=0.25)])
        state = g.run()
        self.assertEqual(state["nodes"]["a"]["status"], "TIMEOUT")
        self.assertNotIn("commit", state["nodes"]["a"])
        self.assertLess(state["nodes"]["a"]["seconds"], 3)
        self.process_not_running(state["nodes"]["a"]["process_pid"])

    def process_not_running(self, pid):
        result = subprocess.run(["/bin/ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
        self.assertTrue(not result.stdout.strip() or result.stdout.strip().startswith("Z"))

    def test_fork_and_detached_subprocess_creation_are_denied(self):
        for mode in ["fork", "detached"]:
            g = self.make([node("a", mode=mode)], name="deny-"+mode)
            g.nodes["a"]["success_pattern"] = "^FORK_DENIED$"
            state = g.run()
            self.assertEqual(state["nodes"]["a"]["status"], "SUCCEEDED")

    def test_cancellation_preserves_checkpoint(self):
        g = self.make([node("a", mode="sleep", timeout=5), node("join", ["a"], writes=[])], limit=1)
        def control():
            deadline = time.monotonic()+3
            while time.monotonic() < deadline:
                s = json.loads((g.directory / "state.json").read_text())
                if s["nodes"]["a"]["status"] == "RUNNING":
                    (g.directory / "cancel.flag").write_text("explicit synthetic cancellation")
                    return
                time.sleep(0.01)
        thread = threading.Thread(target=control); thread.start()
        state = g.run(); thread.join(timeout=2)
        self.assertEqual(state["nodes"]["a"]["status"], "CANCELLED")
        self.assertEqual(state["nodes"]["join"]["status"], "BLOCKED")
        self.assertTrue((g.directory / "state.json").exists())

    def test_write_set_violation_is_retained_and_not_committed(self):
        g = self.make([node("a", mode="escape")])
        state = g.run()
        self.assertEqual(state["nodes"]["a"]["status"], "FAILED")
        self.assertIn("a", g.cleanup())
        self.assertTrue((g.resources["a"] / "worktree/not-allowed.txt").exists())

    def test_conflicting_merges_block_integration(self):
        g = self.make([node("a", mode="conflict-a", writes=["shared.txt"]),
                       node("b", mode="conflict-b", writes=["shared.txt"]),
                       node("join", ["a", "b"], writes=[])])
        state = g.run()
        self.assertEqual(state["nodes"]["a"]["status"], "SUCCEEDED")
        self.assertEqual(state["nodes"]["b"]["status"], "SUCCEEDED")
        self.assertEqual(state["nodes"]["join"]["status"], "PREPARE_FAILED")
        self.assertIn("join", g.cleanup())
        self.assertEqual(git(self.repo, "rev-parse", "HEAD").stdout.strip(), self.base)

    def test_missing_success_evidence_rejects_exit_zero(self):
        state = self.make([node("a", mode="marker")]).run()
        self.assertEqual(state["nodes"]["a"]["exit"], 0)
        self.assertEqual(state["nodes"]["a"]["status"], "FAILED")

    def test_dirty_snapshot_and_runtime_overlap_rejected(self):
        (self.repo / "uncommitted.txt").write_text("synthetic uncommitted input")
        with self.assertRaisesRegex(Rejected, "dirty source"):
            self.make([node("a")])
        (self.repo / "uncommitted.txt").unlink()
        with self.assertRaises(Rejected):
            self.make([node("a")], root=self.repo / "runs")

    def test_run_id_cannot_overwrite_or_take_live_state(self):
        g = self.make([node("a")])
        with self.assertRaises(Rejected): self.make([node("a")])
        with self.assertRaises(Rejected): R["inspect_interrupted"](g.directory)
        with self.assertRaises(Rejected): g.cleanup()

    def test_unknown_recovery_never_replays(self):
        g = self.make([node("a")]); g.state["nodes"]["a"]["status"] = "RUNNING"; g._save(); g.close()
        state = R["inspect_interrupted"](g.directory)
        self.assertEqual(state["status"], "UNKNOWN")
        self.assertEqual(state["nodes"]["a"]["status"], "UNKNOWN")
        self.assertNotIn("a", g.resources)

    def test_repeated_partial_cleanup_preserves_dirty_worktree(self):
        g = self.make([node("a", mode="escape")])
        g.run()
        self.assertEqual(g.cleanup(), ["a"])
        self.assertEqual(g.cleanup(), ["a"])
        self.assertTrue((g.resources["a"] / "worktree/not-allowed.txt").exists())

    def test_scheduler_exception_cancels_before_executor_wait(self):
        g = self.make([node("a", mode="sleep", timeout=4)])
        started = time.monotonic()
        with patch.dict(GraphRun.run.__globals__, {"wait": lambda *a, **k: (_ for _ in ()).throw(RuntimeError("synthetic coordinator failure"))}):
            with self.assertRaises(RuntimeError): g.run()
        self.assertEqual(g.state["status"], "UNKNOWN")
        self.assertTrue(g.cancel.is_set())
        self.assertLess(time.monotonic() - started, 2)
        with self.assertRaises(Rejected): g.cleanup()

    def test_external_candidate_drift_refuses_promotion(self):
        for kind in ["head", "index", "bytes"]:
            with self.subTest(kind=kind):
                g = self.make([node("a")], name="drift-" + kind)
                original = g._execute
                def inject(node, resource):
                    result = original(node, resource)
                    wt = resource / "worktree"
                    (wt / "a.txt").write_text("host changed an already validated artifact")
                    if kind in {"head", "index"}:
                        git(wt, "add", "a.txt")
                        if kind == "head": git(wt, "commit", "-m", "Synthetic out-of-band host change")
                    return result
                g._execute = inject
                state = g.run()
                self.assertEqual(state["nodes"]["a"]["status"], "FAILED")
                self.assertNotIn("commit", state["nodes"]["a"])
                self.assertIn("a", g.cleanup())

    def test_stale_active_capacity_quarantines_new_dispatch(self):
        g = self.make([node("a")], limit=1)
        lease = g.pool.acquire(threading.Event(), time.monotonic()+1)
        # Simulate the durable reservation left by SIGKILL: release OS flock, retain ACTIVE marker.
        R["fcntl"].flock(lease, R["fcntl"].LOCK_UN); lease.close()
        with self.assertRaisesRegex(Rejected, "unknown active"):
            g.pool.acquire(threading.Event(), time.monotonic()+1)
        self.assertTrue((g.pool.area/"quarantine.json").exists())
        with self.assertRaisesRegex(Rejected, "quarantined"):
            g.pool.acquire(threading.Event(), time.monotonic()+1)
        self.assertEqual(g.resources,{})

    def test_filter_rejected_before_status_can_execute_it(self):
        marker=self.root/"filter-marker"
        helper=self.root/"filter.sh";helper.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\ncat\n');helper.chmod(0o700)
        git(self.repo,"config","--local","filter.demo.clean",str(helper))
        (self.repo/".gitattributes").write_text("shared.txt filter=demo\n")
        (self.repo/"shared.txt").write_text("force content comparison")
        with self.assertRaisesRegex(Rejected,"filters/includes"):
            self.make([node("a")])
        self.assertFalse(marker.exists())

    def test_subdirectory_cannot_hide_repository_scope(self):
        child=self.repo/"nested";child.mkdir();(child/"input.txt").write_text("synthetic")
        git(self.repo,"add","nested/input.txt");git(self.repo,"commit","-m","Nested synthetic input")
        with self.assertRaisesRegex(Rejected,"top-level"):
            R["inspect_repo"](child,"HEAD")

    def test_git_boolean_spellings_cannot_enable_worktree_config(self):
        for value in ["true","yes","on","1"]:
            with self.subTest(value=value):
                git(self.repo,"config","--local","extensions.worktreeConfig",value)
                with self.assertRaisesRegex(Rejected,"per-worktree"):
                    R["inspect_repo"](self.repo,self.base)
        # Git treats an explicit empty value as false; a valueless key is true.
        git(self.repo,"config","--local","extensions.worktreeConfig","")
        R["inspect_repo"](self.repo,self.base)
        git(self.repo,"config","--local","--unset","extensions.worktreeConfig")
        with (self.repo/".git/config").open("a") as config:
            config.write("\n[extensions]\n\tworktreeConfig\n")
        with self.assertRaisesRegex(Rejected,"per-worktree"):
            R["inspect_repo"](self.repo,self.base)

    def test_cleanup_guard_precedes_status_filters(self):
        g=self.make([node("a")]);g.run()
        marker=self.root/"cleanup-filter-marker"
        helper=self.root/"cleanup-filter.sh";helper.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\ncat\n');helper.chmod(0o700)
        git(self.repo,"config","--local","filter.demo.clean",str(helper))
        (g.common/"info/attributes").write_text("shared.txt filter=demo\n")
        (g.resources["graph"]/"worktree/shared.txt").touch()
        with self.assertRaisesRegex(Rejected,"configuration drift"):g.cleanup()
        self.assertFalse(marker.exists())

    def test_configuration_drift_rejected_before_host_git(self):
        g=self.make([node("a")])
        git(self.repo,"config","--local","filter.demo.clean","cat")
        with self.assertRaisesRegex(Rejected,"configuration drift"):g.run()
        self.assertEqual(g.state["status"],"REJECTED")
        self.assertFalse((g.directory/"graph/worktree").exists())

    def test_killed_host_leaves_capacity_quarantined(self):
        g=self.make([node("a")],limit=1)
        program="import runpy,pathlib,threading,time,sys; r=runpy.run_path(sys.argv[1]); p=r['LeasePool'](pathlib.Path(sys.argv[2]),1,1); lease=p.acquire(threading.Event(),time.monotonic()+2); print('LEASED',flush=True); time.sleep(30)"
        helper=subprocess.Popen([sys.executable,"-I","-B","-c",program,str(ROOT/"tools/execution/runtime.py"),str(self.root/"runs")],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                env={"PATH":"/usr/bin:/bin","HOME":str(self.root),"LC_ALL":"C"})
        try:
            self.assertEqual(helper.stdout.readline().strip(),"LEASED")
            helper.kill();helper.wait(timeout=2)
            with self.assertRaisesRegex(Rejected,"unknown active"):
                g.pool.acquire(threading.Event(),time.monotonic()+1)
            self.assertTrue((g.pool.area/"quarantine.json").exists())
        finally:
            if helper.poll() is None:helper.kill();helper.wait(timeout=2)
            helper.stdout.close();helper.stderr.close()

    def test_multiple_graphs_share_host_process_capacity(self):
        a = self.make([node("a")], limit=1, name="first", host=1)
        b = self.make([node("b")], limit=1, name="second", host=1)
        with ThreadPoolExecutor(max_workers=2) as pool:
            states = list(pool.map(lambda g: g.run(), [a, b]))
        intervals = [state["nodes"][n] for state, n in zip(states, ["a", "b"])]
        intervals.sort(key=lambda i: i["started_at"])
        self.assertGreaterEqual(intervals[1]["started_at"], intervals[0]["ended_at"] - 0.01)
        for state in states: self.assertEqual(state["status"], "SUCCEEDED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
