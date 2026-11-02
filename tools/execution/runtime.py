"""Instance-owned worktrees and an experimentally probed macOS Seatbelt backend.

Trusted host orchestrator only. This is not a hostile multi-tenant or cross-platform
sandbox. Children cannot operate the shared Git admin directory. Runtime state and
raw output are private, outside the source repository; callers publish only an
explicitly reviewed summary.
"""
from pathlib import Path
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import fcntl
import hashlib
import json
import math
import os
import platform
import re
import signal
import shutil
import subprocess
import sys
import stat
import threading
import time


class Rejected(RuntimeError):
    pass


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", value):
        raise Rejected("invalid execution identifier")
    return value


def relative(value):
    if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_./-]+", value)
            or Path(value).is_absolute() or any(p in {"..", ".git"} for p in Path(value).parts)
            or value.startswith("-") or any(p.startswith(".") for p in Path(value).parts)):
        raise Rejected("invalid relative artifact path")
    return value


def atomic(path, value):
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def git(repo, *args, check=True):
    env = {"PATH": "/usr/bin:/bin", "HOME": "/var/empty", "LC_ALL": "C",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_ATTR_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    command = ["/usr/bin/git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
               "-c", "core.attributesFile=/dev/null", "-c", "commit.gpgsign=false",
               "-c", "user.name=workflow-demo", "-c", "user.email=runner@invalid",
               "-C", str(repo), *args]
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
    if check and result.returncode:
        raise Rejected("Git operation rejected: " + args[0])
    return result


def inspect_repo(repo, base):
    repo = Path(repo).resolve(strict=True)
    if git(repo, "config", "--local", "--no-includes", "--name-only", "--get-regexp",
           r"^(filter\.|include\.|includeif\.)", check=False).stdout:
        raise Rejected("local filters/includes are outside supported trusted-repository scope")
    per_worktree = git(repo, "config", "--local", "--no-includes", "--type=bool", "--get", "extensions.worktreeConfig", check=False)
    if per_worktree.returncode != 1 and (per_worktree.returncode != 0 or per_worktree.stdout.strip() != "false"):
        raise Rejected("per-worktree configuration is not supported")
    if Path(git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve() != repo:
        raise Rejected("explicit repository top-level required")
    common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
    info = common / "info/attributes"
    if info.exists() and info.read_bytes().strip():
        raise Rejected("repository info attributes are not supported")
    frozen = git(repo, "rev-parse", "--verify", base + "^{commit}").stdout.strip()
    for record in git(repo, "ls-tree", "-r", "-z", frozen).stdout.split("\0"):
        if not record:
            continue
        meta, name = record.split("\t", 1)
        relative(name)
        if meta.split()[0] not in {"100644", "100755"} or name in {".gitattributes", ".gitmodules"}:
            raise Rejected("symlinks, submodules or attributes are not supported")
    # Only after static source/config admission may status invoke its normal worktree comparison.
    if git(repo, "status", "--porcelain", "--untracked-files=all").stdout:
        raise Rejected("dirty source workspace; freeze an explicit clean snapshot first")
    return repo, common, frozen


def workspace_identity(worktree):
    files = {}
    for path in sorted(worktree.rglob("*")):
        if path == worktree / ".git": continue
        if path.is_symlink() or not (path.is_dir() or stat.S_ISREG(path.stat().st_mode)):
            raise Rejected("symlink or special-file workspace refused")
        if path.is_file():
            files[path.relative_to(worktree).as_posix()] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "mode": stat.S_IMODE(path.stat().st_mode)}
    return identity(files)


class LeasePool:
    """Cross-process file leases shared by Graphs using the same private runtime root."""
    def __init__(self, root, requested, default):
        self.area = root / "pool"
        self.area.mkdir(exist_ok=True)
        with (self.area / "config.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            config = self.area / "capacity.json"
            if config.exists():
                self.capacity = json.loads(config.read_text())["capacity"]
                if requested is not None and requested != self.capacity:
                    raise Rejected("existing host pool capacity cannot be silently changed")
            else:
                self.capacity = default if requested is None else requested
                if type(self.capacity) is not int or not 1 <= self.capacity <= 16:
                    raise Rejected("invalid host capacity")
                atomic(config, {"capacity": self.capacity})

    def acquire(self, cancel, deadline):
        while time.monotonic() < deadline and not cancel.is_set():
            if (self.area / "quarantine.json").exists():
                raise Rejected("host pool quarantined by an unknown prior process")
            for number in range(self.capacity):
                lease = (self.area / (str(number) + ".lock")).open("a+")
                try:
                    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    lease.seek(0)
                    old = lease.read()
                    try: stale = bool(old) and json.loads(old).get("state") != "released"
                    except ValueError: stale = True
                    if stale:
                        atomic(self.area / "quarantine.json", {"reason": "unknown active process reservation"})
                        fcntl.flock(lease, fcntl.LOCK_UN); lease.close()
                        raise Rejected("unknown active process; no capacity reuse or stale-PID signals")
                    lease.seek(0); lease.truncate()
                    lease.write(json.dumps({"state": "active", "host_pid": os.getpid()}))
                    lease.flush(); os.fsync(lease.fileno())
                    return lease
                except BlockingIOError:
                    lease.close()
            time.sleep(0.02)
        raise Rejected("process lease cancelled or deadline reached")

    @staticmethod
    def release(lease):
        lease.seek(0); lease.truncate()
        lease.write(json.dumps({"state": "released"}))
        lease.flush(); os.fsync(lease.fileno())
        fcntl.flock(lease, fcntl.LOCK_UN)
        lease.close()


class Seatbelt:
    """Deprecated Apple CLI, fail-closed and probed per resource instance.

    Allows system/Python/tool read roots, worktree data, private HOME/TMP,
    filesystem metadata and root-directory enumeration needed by this Python.
    Denies other file contents, shared Git metadata, network and signal operations.
    No memory/total-disk or hostile same-user multi-tenant guarantee.
    """
    def __init__(self, tool_roots=(), pool=None):
        if platform.system() != "Darwin" or not Path("/usr/bin/sandbox-exec").is_file():
            raise Rejected("UNSUPPORTED_SANDBOX: no verified macOS backend; no bare-process fallback")
        self.profiles = {}
        self.pool = pool
        self.python = str(Path(sys.executable).resolve())
        self.roots = [Path(sys.base_prefix).resolve(), Path(self.python).parent,
                      Path("/System"), Path("/usr/lib"), Path("/usr/share/zoneinfo"),
                      Path("/bin"), Path("/private/var/db/dyld")]
        for root in tool_roots:
            value = Path(root).resolve(strict=True)
            if value in {Path("/"), Path.home(), Path("/Users"), Path("/home")}:
                raise Rejected("overbroad tool read root")
            self.roots.append(value)

    def prepare(self, resource, common):
        area = resource / "sandbox"
        area.mkdir()
        for name in ["home", "tmp"]:
            (area / name).mkdir()
        worktree = resource / "worktree"
        if any(common.is_relative_to(root) or resource.is_relative_to(root) for root in self.roots):
            raise Rejected("tool root exposes execution administration")
        q = lambda p: json.dumps(str(p.resolve()))
        rules = ["(version 1)", "(deny default)", "(deny process-fork)", "(allow process-exec)",
                 "(allow sysctl-read)", "(allow file-read-metadata)", "(deny network*)",
                 '(allow file-read* (literal "/"))']
        rules += ["(allow file-read* (subpath " + q(root) + "))" for root in self.roots]
        rules += ["(allow file-read* (subpath " + q(worktree) + "))"]
        rules += ["(allow file-write* (subpath " + q(worktree) + "))"]
        rules += ["(allow file-read* file-write* (subpath " + q(area / name) + "))" for name in ["home", "tmp"]]
        rules += ['(allow file-read* (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random"))',
                  '(allow file-write* (literal "/dev/null"))',
                  "(deny file-read* file-write* (literal " + q(worktree / ".git") + ") (subpath " + q(common) + "))"]
        # Host-owned supervisor limits per-file output and CPU; children cannot edit it.
        supervisor = area / "supervisor.py"
        supervisor.write_text("import os,resource,sys\n"
                              "resource.setrlimit(resource.RLIMIT_FSIZE,(8388608,8388608))\n"
                              "resource.setrlimit(resource.RLIMIT_CPU,(int(sys.argv[1]),int(sys.argv[1])+1))\n"
                              "os.execv(sys.argv[2],sys.argv[2:])\n")
        rules.append("(allow file-read* (literal " + q(supervisor) + "))")
        profile = area / "profile.sb"
        profile.write_text("\n".join(rules) + "\n")
        self.profiles[str(resource)] = hashlib.sha256(profile.read_bytes()).hexdigest()
        return profile

    def execute(self, resource, command, timeout, cancel, extra_env=None, log_name="command"):
        area = resource / "sandbox"
        if hashlib.sha256((area / "profile.sb").read_bytes()).hexdigest() != self.profiles[str(resource)]:
            raise Rejected("sandbox policy changed after preparation")
        # No host HOME, tokens, proxy credentials, Git/Maven/JVM injection or shared caches.
        env = {"PATH": "/usr/bin:/bin", "HOME": str(area / "home"), "TMPDIR": str(area / "tmp"),
               "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}
        if extra_env:
            env.update(extra_env)  # Host-only fixed probe values; never taken from node definitions.
        full = ["/usr/bin/sandbox-exec", "-f", str(area / "profile.sb"), self.python, "-I", "-B",
                str(area / "supervisor.py"), str(max(1, math.ceil(timeout))), *command]
        log = area / (log_name + ".log")
        started = time.monotonic()
        try:
            lease = self.pool.acquire(cancel, started + timeout) if self.pool else None
        except Rejected:
            return {"exit": None, "reason": "CANCELLED" if cancel.is_set() else "TIMEOUT",
                    "seconds": time.monotonic() - started, "started_at": None, "ended_at": None,
                    "text": "", "log_sha256": None}
        process = None
        try:
            with log.open("wb") as output:
                process_started = time.monotonic()
                process = subprocess.Popen(full, cwd=resource / "worktree", env=env,
                                           stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                reason = None
                while process.poll() is None:
                    if cancel.is_set(): reason = "CANCELLED"
                    elif time.monotonic() - started >= timeout: reason = "TIMEOUT"
                    if reason:
                        try: os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                        break
                    time.sleep(0.02)
                process.wait()
                # A command is not done while it leaves background descendants in its group.
                try:
                    os.killpg(process.pid, 0)
                    os.killpg(process.pid, signal.SIGKILL)
                    reason = reason or "BACKGROUND_PROCESS"
                except ProcessLookupError:
                    pass
        finally:
            # An exception never releases a reservation while its known foreground process is alive.
            if process is not None and process.poll() is None:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait()
            if lease: self.pool.release(lease)
        size = log.stat().st_size
        text = log.read_bytes()[:65536].decode("utf-8", errors="replace")
        if size > 65536: reason = reason or "OUTPUT_LIMIT"
        return {"exit": process.returncode, "reason": reason, "seconds": time.monotonic() - started,
                "started_at": process_started, "ended_at": time.monotonic(), "process_pid": process.pid, "text": text, "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()}

    def probe(self, resource, common):
        outside = resource.parent / (resource.name + "-canary")
        outside.write_text("independently constructed canary")
        admin = common / ("workflow-probe-" + hashlib.sha256(str(resource).encode()).hexdigest()[:24])
        with admin.open("x") as file: file.write("synthetic Git-admin canary")
        script = resource / "sandbox/home/probe.py"
        script.write_text('''import os,pathlib,socket
pathlib.Path("sandbox-positive").write_text("allowed")
for path in [os.environ["CANARY"], os.environ["GIT_ADMIN"]]:
    try:
        pathlib.Path(path).read_bytes()
        raise RuntimeError("read isolation failed")
    except PermissionError: pass
for path in [os.environ["CANARY"], os.environ["GIT_ADMIN"]]:
    try:
        pathlib.Path(path).write_text("changed")
        raise RuntimeError("write isolation failed")
    except PermissionError: pass
try:
    os.link(os.environ["CANARY"], "probe-hardlink")
    raise RuntimeError("outside hardlink permitted")
except PermissionError: pass
try:
    pathlib.Path("probe-symlink").symlink_to(os.environ["CANARY"])
    pathlib.Path("probe-symlink").read_bytes()
    raise RuntimeError("outside symlink read permitted")
except PermissionError: pass
finally:
    pathlib.Path("probe-symlink").unlink(missing_ok=True)
try:
    socket.socket().connect(("127.0.0.1",9))
    raise RuntimeError("network isolation failed")
except PermissionError: pass
import subprocess,sys
for detached in [False,True]:
    try:
        child=subprocess.Popen([sys.executable,"-I","-B","-c","pass"],start_new_session=detached)
        child.wait()
        raise RuntimeError("child-process creation permitted")
    except PermissionError: pass
print("PROBE_OK")
''')
        try:
            result = self.execute(resource, [self.python, "-I", "-B", str(script)], 10, threading.Event(),
                                  {"CANARY": str(outside), "GIT_ADMIN": str(admin)}, "probe")
            if admin.read_text() != "synthetic Git-admin canary":
                raise Rejected("SANDBOX_PROBE_CHANGED_ADMIN_CANARY")
        finally:
            admin.unlink(missing_ok=True)
        if result["exit"] or result["reason"] or "PROBE_OK" not in result["text"]:
            raise Rejected("SANDBOX_PROBE_FAILED; no workflow command dispatched")
        (resource / "worktree/sandbox-positive").unlink()
        if outside.read_text() != "independently constructed canary":
            raise Rejected("SANDBOX_PROBE_CHANGED_CANARY")
        outside.unlink()
        return {"positive_write": True, "outside_read_denied": True, "outside_write_denied": True,
                "git_admin_read_denied": True, "git_admin_write_denied": True, "network_denied": True,
                "outside_hardlink_denied": True, "outside_symlink_read_denied": True,
                "fork_denied": True, "detached_child_denied": True}


def validate(definition):
    if set(definition) != {"graph_id", "max_parallel", "nodes"}:
        raise Rejected("unknown Graph fields")
    token(definition["graph_id"])
    limit = definition["max_parallel"]
    if type(limit) is not int or not 1 <= limit <= 16:
        raise Rejected("invalid shared concurrency limit")
    nodes = definition["nodes"]
    if not isinstance(nodes, list) or not nodes:
        raise Rejected("empty Graph")
    by_id = {}
    for node in nodes:
        if set(node) != {"id", "depends_on", "command", "allowed_write", "success_pattern", "timeout"}:
            raise Rejected("unknown Workflow fields; nested Graphs are not supported")
        name = token(node["id"])
        if name == "graph": raise Rejected("reserved Graph resource name")
        if name in by_id: raise Rejected("duplicate Workflow instance")
        if not isinstance(node["depends_on"], list) or len(set(node["depends_on"])) != len(node["depends_on"]):
            raise Rejected("invalid dependencies")
        if not isinstance(node["command"], list) or not node["command"] or not all(isinstance(x, str) for x in node["command"]):
            raise Rejected("command must be an argv list; no shell string")
        if not isinstance(node["allowed_write"], list): raise Rejected("invalid write set")
        for path in node["allowed_write"]: relative(path)
        if not isinstance(node["success_pattern"], str) or not node["success_pattern"]:
            raise Rejected("success evidence pattern required")
        if not re.fullmatch(r"\^[A-Za-z0-9 _=,.:/-]{1,200}\$", node["success_pattern"]):
            raise Rejected("success pattern must be an anchored literal line, not a general regex")
        if type(node["timeout"]) not in {int, float} or not 0.1 <= node["timeout"] <= 600:
            raise Rejected("invalid finite deadline")
        by_id[name] = node
    done = set()
    while len(done) != len(nodes):
        ready = {key for key, n in by_id.items() if key not in done and set(n["depends_on"]) <= done}
        if not ready: raise Rejected("cyclic or missing dependency")
        done.update(ready)
    return by_id


class GraphRun:
    """One deterministic DAG and one shared concurrency budget, not an LLM scheduler.

    The main thread alone writes the checkpoint. Children never receive state,
    source-repository administration, credentials or sibling workspace mounts.
    """
    def __init__(self, repo, base, runtime_root, definition, tool_roots=(), java_home=None, host_capacity=None):
        self.nodes = validate(definition)
        self.repo, self.common, self.base = inspect_repo(repo, base)
        self.config_id = hashlib.sha256((self.common / "config").read_bytes()).hexdigest()
        self.root = Path(runtime_root).resolve()
        if self.root.is_relative_to(self.repo) or self.repo.is_relative_to(self.root):
            raise Rejected("runtime root must be outside and not contain source repository")
        if self.root in {Path("/"), Path.home(), Path("/Users"), Path("/home")}:
            raise Rejected("overbroad runtime root")
        if self.root.exists() and any(self.root.iterdir()) and not (self.root / ".execution-root").is_file():
            raise Rejected("runtime root contains unrelated files")
        self.root.mkdir(parents=True, exist_ok=True)
        marker = self.root / ".execution-root"
        if not marker.exists(): marker.write_text("execution-root-v1\n")
        if marker.read_text() != "execution-root-v1\n": raise Rejected("unknown runtime root")
        self.pool = LeasePool(self.root, host_capacity, definition["max_parallel"])
        if definition["max_parallel"] > self.pool.capacity: raise Rejected("Graph limit exceeds host pool")
        self.backend = Seatbelt(tool_roots, self.pool)
        self.directory = self.root / token(definition["graph_id"])
        try: self.directory.mkdir()
        except FileExistsError: raise Rejected("run_id already exists; never overwrite an instance")
        os.chmod(self.directory, 0o700)
        self.lock = (self.directory / "owner.lock").open("x")
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.definition = definition
        self.java_home = Path(java_home).resolve() if java_home else None
        self.cancel = threading.Event()
        self.state = {"graph_id": definition["graph_id"], "definition_id": identity(definition),
                      "base_commit": self.base, "status": "CREATED", "max_parallel": definition["max_parallel"], "host_capacity": self.pool.capacity,
                      "peak_parallel": 0, "nodes": {name: {"status": "PENDING", "run_id": definition["graph_id"] + "/" + name, "parent_run_id": definition["graph_id"]} for name in self.nodes},
                      "events": [], "cleanup": "not_requested"}
        self.resources = {}
        self.results = {}
        self.expected_heads = {}
        self.git_pointers = {}
        self._save()

    def _save(self):
        atomic(self.directory / "state.json", self.state)

    def _event(self, node, state):
        self.state["events"].append({"sequence": len(self.state["events"]) + 1, "node": node,
                                     "status": state, "at": time.monotonic()})
        self._save()

    @contextmanager
    def _git_lease(self):
        path = self.common / "ai-workflow-execution.lock"
        if path.is_symlink(): raise Rejected("Git administration lease is a symlink")
        with path.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if hashlib.sha256((self.common / "config").read_bytes()).hexdigest() != self.config_id:
                raise Rejected("repository configuration drift after admission")
            attrs = self.common / "info/attributes"
            if attrs.exists() and attrs.read_bytes().strip():
                raise Rejected("repository attributes drift after admission")
            yield

    def _prepare(self, name, deps):
        resource = self.directory / name
        resource.mkdir()
        branch = "execution/" + self.definition["graph_id"] + "/" + name
        with self._git_lease():
            git(self.repo, "worktree", "add", "-b", branch, str(resource / "worktree"), self.base)
            self.resources[name] = resource
            # Host broker serializes the shared Git administration and merges frozen dependency commits.
            for dependency in deps:
                commit = self.results[dependency]["commit"]
                result = git(resource / "worktree", "merge", "--no-edit", "--no-ff", commit, check=False)
                if result.returncode: raise Rejected("INTEGRATION_CONFLICT: explicit resolution required")
            self.git_pointers[name] = (resource / "worktree/.git").read_bytes()
            self.expected_heads[name] = git(resource / "worktree", "rev-parse", "HEAD").stdout.strip()
        self.backend.prepare(resource, self.common)
        probe = self.backend.probe(resource, self.common)
        return resource, branch, probe

    def _execute(self, node, resource):
        command = []
        for value in node["command"]:
            if value == "{python}": value = self.backend.python
            elif value == "{java-tmp-option}":
                value = "-Djava.io.tmpdir=" + str(resource / "sandbox/tmp")
            elif value == "{java}":
                if self.java_home is None: raise Rejected("JDK path required")
                value = str(self.java_home / "bin/java")
            elif value == "{javac}":
                if self.java_home is None: raise Rejected("JDK path required")
                value = str(self.java_home / "bin/javac")
            command.append(value)
        result = self.backend.execute(resource, command, node["timeout"], self.cancel)
        result["workspace_id"] = workspace_identity(resource / "worktree")
        result["success"] = (result["exit"] == 0 and result["reason"] is None
                             and node["success_pattern"][1:-1] in result["text"].splitlines())
        return result

    def _complete(self, name, node, result):
        resource = self.resources[name]
        result.pop("text", None)  # Raw output remains local, never part of public checkpoint receipts.
        if not result["success"]:
            result["status"] = result["reason"] or "FAILED"
            self.state["nodes"][name].update(result)
            return
        wt = resource / "worktree"
        for p in wt.rglob("*"):
            if p.is_symlink() or not (p.is_dir() or stat.S_ISREG(p.stat().st_mode)):
                raise Rejected("symlink or special-file output refused")
        # Strict logical write set supplements the physical workspace sandbox boundary.
        with self._git_lease():
            if (wt / ".git").read_bytes() != self.git_pointers[name]:
                raise Rejected("worktree administration pointer drift")
            if git(wt, "rev-parse", "HEAD").stdout.strip() != self.expected_heads[name]:
                raise Rejected("candidate HEAD drift after validation")
            if git(wt, "diff", "--cached", "--name-only").stdout:
                raise Rejected("unexpected pre-staged changes")
            if workspace_identity(wt) != result["workspace_id"]:
                raise Rejected("validated workspace content drift")
            changed = git(wt, "diff", "--name-only", "--no-renames").stdout.splitlines()
            untracked = git(wt, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
            ignored = git(wt, "ls-files", "--others", "--ignored", "--exclude-standard").stdout.splitlines()
            if not set(changed + untracked + ignored) <= set(node["allowed_write"]):
                raise Rejected("write set exceeded; output retained, no commit")
            for path in node["allowed_write"]:
                if (wt / path).exists() or path in changed:
                    git(wt, "add", "--", path)
            if git(wt, "diff", "--cached", "--name-only").stdout:
                git(wt, "commit", "-m", "Complete synthetic Workflow " + name)
            commit = git(wt, "rev-parse", "HEAD").stdout.strip()
        result.update(status="SUCCEEDED", commit=commit)
        self.results[name] = result
        self.state["nodes"][name].update(result)

    def run(self):
        if self.state["status"] != "CREATED": raise Rejected("execution instance cannot be replayed")
        self.state["status"] = "RUNNING"
        # The Graph also owns a real worktree/sandbox, but does not consume a worker slot while scheduling.
        try:
            _, branch, probe = self._prepare("graph", [])
            self.state["graph_resource"] = {"branch": branch, "probe": probe}
        except Exception as e:
            self.state["status"] = "REJECTED"; self._save(); raise
        futures = {}
        pool = ThreadPoolExecutor(max_workers=self.definition["max_parallel"])
        try:
            while True:
                if (self.directory / "cancel.flag").exists(): self.cancel.set()
                for name, node in self.nodes.items():
                    if self.state["nodes"][name]["status"] != "PENDING": continue
                    deps = [self.state["nodes"][d]["status"] for d in node["depends_on"]]
                    if self.cancel.is_set() or any(s not in {"PENDING", "RUNNING", "SUCCEEDED"} for s in deps):
                        self.state["nodes"][name]["status"] = "BLOCKED"
                        self._event(name, "BLOCKED")
                    elif all(s == "SUCCEEDED" for s in deps) and len(futures) < self.definition["max_parallel"]:
                        self.state["nodes"][name]["status"] = "PREPARING"
                        self._event(name, "PREPARING")
                        try:
                            resource, branch, probe = self._prepare(name, node["depends_on"])
                            self.state["nodes"][name].update(status="RUNNING", branch=branch, probe=probe,
                                                             input_commit=self.expected_heads[name])
                            self._event(name, "RUNNING")
                            futures[pool.submit(self._execute, node, resource)] = name
                            self.state["peak_parallel"] = max(self.state["peak_parallel"], len(futures))
                        except Exception as exc:
                            self.state["nodes"][name].update(status="PREPARE_FAILED", failure_type=type(exc).__name__)
                            self._event(name, "PREPARE_FAILED")
                if not futures:
                    if all(s["status"] != "PENDING" for s in self.state["nodes"].values()): break
                else:
                    finished, _ = wait(futures, timeout=0.02, return_when=FIRST_COMPLETED)
                    for future in finished:
                        name = futures.pop(future)
                        try: self._complete(name, self.nodes[name], future.result())
                        except Exception as exc:
                            self.state["nodes"][name].update(status="FAILED", failure_type=type(exc).__name__)
                        self._event(name, self.state["nodes"][name]["status"])
                if not futures and any(s["status"] == "PENDING" for s in self.state["nodes"].values()):
                    # A failed prerequisite may have been seen later in this insertion order; propagate next iteration.
                    continue
            self.state["status"] = "SUCCEEDED" if all(v["status"] == "SUCCEEDED" for v in self.state["nodes"].values()) else "INCOMPLETE"
            self._save()
        except BaseException:
            # Cancel before waiting on the executor, including failed checkpoint writes.
            self.cancel.set()
            self.state["status"] = "UNKNOWN"
            try: self._save()
            except OSError: pass  # The last durable RUNNING checkpoint is deliberately not treated as success.
            raise
        finally:
            pool.shutdown(wait=True)
        return self.state

    def cleanup(self):
        if self.lock.closed: raise Rejected("cleanup requires the live owner lease")
        if self.state["status"] in {"RUNNING", "CREATED", "UNKNOWN"}:
            raise Rejected("live or unknown execution cannot be cleaned")
        if self.state["cleanup"] == "worktrees_removed": return []
        retained = []
        stages = self.state.setdefault("resource_cleanup", {})
        for name, resource in self.resources.items():
            if stages.get(name) == "cleaned": continue
            wt = resource / "worktree"
            if stages.get(name) != "worktree_removed":
                if not wt.is_dir():
                    retained.append(name); continue  # Never infer that an externally missing path is safely cleaned.
                if (wt / ".git").is_symlink() or (wt / ".git").read_bytes() != self.git_pointers.get(name):
                    retained.append(name); continue
                with self._git_lease():
                    expected = self.results.get(name, {}).get("commit", self.expected_heads.get(name))
                    if expected is None or git(wt, "rev-parse", "HEAD").stdout.strip() != expected:
                        retained.append(name); continue
                    if git(wt, "status", "--porcelain", "--untracked-files=all", "--ignored").stdout:
                        retained.append(name); continue
                    git(self.repo, "worktree", "remove", str(wt))
                stages[name] = "worktree_removed"
                self._save()
            for child in ["home", "tmp"]:
                area = resource / "sandbox" / child
                if area.is_symlink(): raise Rejected("cleanup boundary changed")
                if area.exists(): shutil.rmtree(area)
            stages[name] = "cleaned"
            self._save()
        self.state["cleanup"] = "retained_dirty" if retained else "worktrees_removed"
        self.state["retained"] = retained
        self._save()
        return retained

    def close(self):
        if self.lock.closed: return
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()


def inspect_interrupted(directory):
    """Recover an audit checkpoint only. Never replay unknown commands or kill stale PIDs."""
    directory = Path(directory).resolve(strict=True)
    with (directory / "owner.lock").open("r+") as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise Rejected("execution still owned by a live host")
        state = json.loads((directory / "state.json").read_text())
        for value in state["nodes"].values():
            if value["status"] in {"RUNNING", "PREPARING"}: value["status"] = "UNKNOWN"
        if any(v["status"] == "UNKNOWN" for v in state["nodes"].values()): state["status"] = "UNKNOWN"
        atomic(directory / "state.json", state)
        return state
