"""Opt-in macOS sandbox for trusted foreground build trees; not a container.

The strict no-fork backend remains unchanged. The observer sees PID/parent/group/
start metadata only, never host command lines or environments. Rapid unobserved
reparenting and adversarial native code are outside this cooperative build mode.
"""
from pathlib import Path
import fcntl
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import threading
import time
from .build_cache import verify as verify_cache
from .runtime import GraphRun, Seatbelt, Rejected, atomic, workspace_identity


def process_table():
    result = subprocess.run(["/bin/ps", "-axo", "pid=,ppid=,pgid=,stat=,lstart="],
                            capture_output=True, text=True, timeout=5,
                            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
    if result.returncode: raise Rejected("process observation unavailable")
    table = {}
    for line in result.stdout.splitlines():
        fields = line.split(None, 4)
        if len(fields) == 5:
            pid, parent, group = map(int, fields[:3])
            table[pid] = (parent, group, fields[3], fields[4])
    return table


class BuildTree:
    def __init__(self, pid):
        self.pid = pid
        self.known = {}
        self.peak = 1
        self.child_seen = False
        self.detached = False

    def live(self):
        table = process_table()
        selected = {p for p, v in table.items() if v[1] == self.pid}
        selected.update(p for p, birth in self.known.items() if p in table and table[p][3] == birth)
        while True:
            extra = {p for p, v in table.items() if v[0] in selected}
            if extra <= selected: break
            selected.update(extra)
        live = {}
        for p in selected:
            row = table[p]
            if p in self.known and self.known[p] != row[3]:
                raise Rejected("observed PID identity changed; no stale-PID signal")
            self.known[p] = row[3]
            if p != self.pid:
                self.child_seen = True
                if row[1] != self.pid: self.detached = True
            if not row[2].startswith("Z"): live[p] = row
        self.peak = max(self.peak, len(live))
        return live

    def stop(self):
        # Only currently observed members with the same birth identity are signalled.
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            live = self.live()
            if not live: return True
            for pid, row in live.items():
                now = process_table().get(pid)
                if now and now[3] == row[3]:
                    try: os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError: pass
            time.sleep(.02)
        return not self.live()


class BuildSeatbelt(Seatbelt):
    def __init__(self, tool_roots=(), pool=None, toolchain=None, allow_observed_daemon=False):
        super().__init__(tool_roots, pool)
        self.toolchain = toolchain or {}
        self.allow_observed_daemon = allow_observed_daemon
        self.unsafe_resources = set()

    def prepare(self, resource, common):
        profile = super().prepare(resource, common)
        text = profile.read_text().replace("(deny process-fork)", "(allow process-fork)")
        # Gradle worker IPC uses localhost. External networking stays denied.
        text += '\n(allow network-inbound (local ip "localhost:*"))\n'
        text += '(allow network-outbound (remote ip "localhost:*"))\n'
        text += '(allow signal (target children))\n'
        profile.write_text(text)
        supervisor = resource / "sandbox/supervisor.py"
        supervisor.write_text(supervisor.read_text().replace("8388608", "268435456"))
        self.profiles[str(resource)] = hashlib.sha256(profile.read_bytes()).hexdigest()
        return profile

    def execute(self, resource, command, timeout, cancel, extra_env=None, log_name="command"):
        area = resource / "sandbox"
        if hashlib.sha256((area / "profile.sb").read_bytes()).hexdigest() != self.profiles[str(resource)]:
            raise Rejected("sandbox policy drift")
        env = {"PATH": "/usr/bin:/bin", "HOME": str(area / "home"), "TMPDIR": str(area / "tmp"),
               "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1",
               "GRADLE_USER_HOME": str(area / "home/gradle"),
               **{key: str(value) for key, value in self.toolchain.items()}}
        if extra_env: env.update(extra_env)
        full = ["/usr/bin/sandbox-exec", "-f", str(area / "profile.sb"), self.python, "-I", "-B",
                str(area / "supervisor.py"), str(max(1, math.ceil(timeout))), *command]
        started = time.monotonic(); lease = None; process = None; tree = None; quiescent = False
        reason = None; log = area / (log_name + ".log")
        try:
            try:
                lease = self.pool.acquire(cancel, started + timeout) if self.pool else None
            except Rejected:
                if self.pool and (self.pool.area / "quarantine.json").exists(): reason = "POOL_QUARANTINED"
                else: reason = "CANCELLED" if cancel.is_set() else "TIMEOUT"
                return {"exit": None, "reason": reason, "seconds": time.monotonic()-started,
                        "started_at": None, "ended_at": None, "text": "", "log_sha256": None,
                        "child_seen": False, "observed_process_peak": 0, "tree_stopped": True}
            with log.open("wb") as output:
                began = time.monotonic()
                process = subprocess.Popen(full, cwd=resource / "worktree", env=env,
                                           stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                tree = BuildTree(process.pid)
                while True:
                    tree.live()
                    if cancel.is_set(): reason = "CANCELLED"
                    elif time.monotonic() - started >= timeout: reason = "TIMEOUT"
                    elif tree.detached and not self.allow_observed_daemon: reason = "DETACHED_PROCESS"
                    if reason or process.poll() is not None: break
                    time.sleep(.02)
                # Opt-in single-use daemon may finish just after its foreground client.
                drain = time.monotonic() + (3 if self.allow_observed_daemon else 0)
                while reason is None and process.poll() is not None and tree.live() and time.monotonic() < drain:
                    if cancel.is_set(): reason = "CANCELLED"; break
                    if time.monotonic()-started >= timeout: reason = "TIMEOUT"; break
                    time.sleep(.02)
                if process.poll() is not None and tree.live(): reason = reason or "BACKGROUND_PROCESS"
                quiescent = tree.stop()
                process.wait(timeout=5)
                if not quiescent: reason = "PROCESS_UNKNOWN"
        except BaseException:
            # The live Popen owner still identifies its own group; stop it even
            # if host observation failed, while retaining the unknown lease.
            if process is not None and process.poll() is None:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait(timeout=5)
            if tree:
                try: quiescent = tree.stop()
                except Exception: quiescent = False
            if process is None: quiescent = True
            raise
        finally:
            if lease:
                if quiescent:
                    self.pool.release(lease)
                else:
                    self.unsafe_resources.add(str(resource))
                    atomic(self.pool.area / "quarantine.json", {"reason": "build tree not confirmed stopped"})
                    fcntl.flock(lease, fcntl.LOCK_UN); lease.close()  # ACTIVE stays durable.
        data = log.read_bytes()
        if len(data) > 65536: reason = reason or "OUTPUT_LIMIT"
        return {"exit": process.returncode, "reason": reason, "seconds": time.monotonic() - started,
                "started_at": began, "ended_at": time.monotonic(), "process_pid": process.pid,
                "text": data[:65536].decode("utf-8", errors="replace"),
                "log_sha256": hashlib.sha256(data).hexdigest(), "child_seen": tree.child_seen,
                "observed_process_peak": tree.peak, "tree_stopped": quiescent,
                "observed_detached": tree.detached, "allow_observed_daemon": self.allow_observed_daemon}

    def probe(self, resource, common):
        outside = resource.parent / (resource.name + "-canary")
        outside.write_text("independent synthetic canary")
        admin = common / ("build-probe-" + hashlib.sha256(str(resource).encode()).hexdigest()[:24])
        with admin.open("x") as file: file.write("synthetic admin canary")
        script = resource / "sandbox/home/probe.py"
        script.write_text('''import pathlib,os,sys,subprocess,socket
pathlib.Path("build-positive").write_text("allowed")
child = """import pathlib,os,socket
for key in ['CANARY','ADMIN']:
 p=pathlib.Path(os.environ[key])
 for action in [lambda:p.read_bytes(),lambda:p.write_text('changed')]:
  try: action();raise RuntimeError('boundary failed')
  except PermissionError:pass
try:
 socket.socket().connect(('192.0.2.1',9));raise RuntimeError('external network permitted')
except PermissionError:pass
print('CHILD_ISOLATED')
"""
p=subprocess.run([sys.executable,'-I','-B','-c',child],capture_output=True,text=True)
assert p.returncode==0 and p.stdout.strip()=='CHILD_ISOLATED'
# Positive IPC uses only our own server's fresh port; no other host service.
s=socket.socket();s.bind(('127.0.0.1',0));s.listen(1)
c=socket.socket();c.connect(s.getsockname());a,_=s.accept();c.close();a.close();s.close()
print('BUILD_PROBE_OK')
''')
        try:
            result = self.execute(resource, [self.python, "-I", "-B", str(script)], 20,
                                  threading.Event(), {"CANARY": str(outside), "ADMIN": str(admin)}, "probe")
            if result["exit"] or result["reason"] or "BUILD_PROBE_OK" not in result["text"]:
                raise Rejected("build sandbox probe failed")
            if outside.read_text() != "independent synthetic canary" or admin.read_text() != "synthetic admin canary":
                raise Rejected("probe canary drift")
        finally:
            admin.unlink(missing_ok=True); outside.unlink(missing_ok=True)
        (resource / "worktree/build-positive").unlink()
        return {key: True for key in ["positive_write", "child_exec_succeeded", "child_outside_read_denied",
                "child_outside_write_denied", "child_admin_read_denied", "child_admin_write_denied",
                "child_external_network_denied", "own_loopback_ipc_succeeded", "observed_tree_stopped"]}


class BuildGraphRun(GraphRun):
    """Explicit trusted build mode, preserving strict runtime source identities."""
    def __init__(self, *args, toolchain=None, cache_seeds=None, allow_observed_daemon=False, **kwargs):
        prepared = {}
        repo = Path(args[0] if args else kwargs["repo"]).resolve(strict=True)
        for name, seed in (cache_seeds or {}).items():
            if name not in {"maven", "gradle"}: raise Rejected("unknown cache seed")
            seed = Path(seed).resolve(strict=True)
            if not seed.is_dir() or seed == Path.home() or seed.is_relative_to(repo):
                raise Rejected("cache seed must be explicit isolated directory")
            try: verify_cache(seed, name)
            except (OSError, ValueError) as exc: raise Rejected("public cache marker missing or invalid") from exc
            prepared[name] = seed
        super().__init__(*args, **kwargs)
        self.backend = BuildSeatbelt(kwargs.get("tool_roots", ()), self.pool, toolchain, allow_observed_daemon)
        self.cache_seeds = prepared
        self.state["execution_mode"] = "trusted_macos_build_tree"
        self._save()

    def _execute(self, node, resource):
        for kind, seed in self.cache_seeds.items():
            verify_cache(seed, kind)
            destination = resource / "sandbox/home" / kind
            shutil.copytree(seed, destination)
            verify_cache(destination, kind)  # Verify the actual copied snapshot before execution.
        return super()._execute(node, resource)

    def cleanup(self):
        if self.backend.unsafe_resources:
            raise Rejected("unknown build processes; retain resources and pool")
        return super().cleanup()
