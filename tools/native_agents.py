"""Codex native collaboration adapter. Private rollout bytes never become public evidence."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import uuid


class NativeRejected(RuntimeError):
    pass


def rows(path, limit=16 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise NativeRejected("missing, linked or oversized protocol log")
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except (ValueError, UnicodeError) as exc:
        raise NativeRejected("unreadable protocol log") from exc


def native_completion(transcript, role):
    """Accept actual tool-call/output pairs, never a parent's success assertion."""
    calls, spawns, listings, seen = {}, [], [], set()
    permitted = {"spawn_agent", "wait_agent", "list_agents"}
    for record in transcript:
        if record.get("type") != "response_item":
            continue
        item = record.get("payload", {})
        if str(item.get("type", "")).endswith("_call") and item.get("type") != "function_call":
            raise NativeRejected("parent performed a non-delegation tool call")
        if item.get("type") == "function_call":
            if item.get("namespace") != "collaboration" or item.get("name") not in permitted:
                raise NativeRejected("parent tool outside dispatcher contract")
            call = item.get("call_id")
            if not call or call in seen:
                raise NativeRejected("duplicate or absent native call id")
            seen.add(call)
            args = json.loads(item["arguments"])
            calls[call] = (item["name"], args)
        elif item.get("type") == "function_call_output" and item.get("call_id") in calls:
            name, args = calls.pop(item["call_id"])
            output = json.loads(item["output"])
            if name == "spawn_agent":
                if args.get("agent_type") != role or args.get("fork_turns") != "none":
                    raise NativeRejected("wrong role or inherited task context")
                task = output.get("task_name")
                if not isinstance(task, str) or not task.startswith("/root/"):
                    raise NativeRejected("native spawn did not return a child identity")
                spawns.append(task)
            elif name == "list_agents" and spawns:
                listings.append(output)
    if calls:
        raise NativeRejected("native tool result missing")
    if len(spawns) != 1:
        raise NativeRejected("exactly one successful native spawn required")
    task = spawns[0]
    completed = None
    for listing in listings:
        for agent in listing.get("agents", []):
            if agent.get("agent_name") == task:
                state = agent.get("agent_status")
                completed = state.get("completed") if isinstance(state, dict) else None
    if not isinstance(completed, str):
        raise NativeRejected("native child completion unconfirmed")
    try:
        result = json.loads(completed)
    except ValueError as exc:
        raise NativeRejected("child result must be a JSON object") from exc
    if (not isinstance(result, dict) or set(result) != {"status", "summary", "outputs"}
            or result["status"] not in {"passed", "failed"}
            or not isinstance(result["summary"], str)
            or not isinstance(result["outputs"], list)
            or any(not isinstance(x, str) for x in result["outputs"])):
        raise NativeRejected("invalid child result contract")
    if result["status"] != "passed":
        raise NativeRejected("native child reported failure")
    return {"role": role, "child_id_sha256": hashlib.sha256(task.encode()).hexdigest(),
            "spawn_calls": 1, "native_completed": True, "result": result}


def own_rollout(session_root, thread_id):
    """Read only the exact newly-created thread, within its UUID timestamp dates."""
    try:
        identifier = uuid.UUID(thread_id)
        if identifier.version != 7:
            raise ValueError("UUIDv7 required")
        day = datetime.fromtimestamp((identifier.int >> 80) / 1000, timezone.utc)
    except (ValueError, TypeError, OverflowError) as exc:
        raise NativeRejected("unsupported thread identity") from exc
    root = Path(session_root).resolve(strict=True)
    matches = []
    for delta in (-1, 0, 1):
        directory = root / (day + timedelta(days=delta)).strftime("%Y/%m/%d")
        matches.extend(directory.glob("rollout-*" + str(identifier) + ".jsonl"))
    if len(matches) != 1 or not matches[0].resolve().is_relative_to(root):
        raise NativeRejected("own native rollout not uniquely available")
    return matches[0]


def dispatch(cwd, role, task, run_dir, codex="codex", session_root=None, timeout=600):
    """Run one native child in an already-authorized public/synthetic workspace."""
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", role):
        raise NativeRejected("invalid native role")
    if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 3600:
        raise NativeRejected("timeout outside supported bounds")
    cwd = Path(cwd).resolve(strict=True)
    run_dir = Path(run_dir).resolve()
    if run_dir.exists() or run_dir.is_relative_to(cwd):
        raise NativeRejected("new private run directory outside workspace required")
    run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    run_dir = run_dir.resolve(strict=True)
    if run_dir.is_relative_to(cwd):
        raise NativeRejected("resolved private run directory inside workspace")
    state = {"status": "UNKNOWN", "role": role, "protocol": "codex-collaboration-rollout-v1"}
    state_file = run_dir / "state.json"
    state_file.write_text(json.dumps(state, indent=2) + "\n")
    prompt = (
        "You are a dispatcher only. Use native collaboration.spawn_agent exactly once with "
        "agent_type=" + role + ", fork_turns=none and task_name=stage. Do not execute shell, "
        "edit files, impersonate a role, or use any substitute agent. Pass the following task "
        "verbatim. Wait until the child finishes, then call collaboration.list_agents so its "
        "actual completed result is recorded. Only spawn_agent, wait_agent and list_agents "
        "are permitted parent tools. If unavailable stop. The child must return ONLY JSON "
        "with exactly status (passed or failed), summary (string), outputs (relative paths array). "
        "Do not close the child before list_agents. Task:\n" + task +
        "\nReturn ONLY the specified JSON as the child's final response."
    )
    command = [str(codex), "exec", "--json", "--skip-git-repo-check", "--sandbox", "workspace-write",
               "-c", 'approval_policy="never"', "-C", str(cwd), prompt]
    process = None
    try:
        with (run_dir / "events.jsonl").open("wb") as stdout, (run_dir / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if time.monotonic() >= deadline or stdout.tell() + stderr.tell() > 16 * 1024 * 1024:
                    raise NativeRejected("native timeout/log bound; child state UNKNOWN, do not retry")
                time.sleep(0.1)
        if sum((run_dir / name).stat().st_size for name in ["events.jsonl", "stderr.log"]) > 16 * 1024 * 1024:
            raise NativeRejected("native final log bound exceeded")
        events = rows(run_dir / "events.jsonl")
        if process.returncode != 0 or any(x.get("type") in {"error", "turn.failed"} for x in events):
            raise NativeRejected("native process failed; private evidence retained")
        ids = [x.get("thread_id") for x in events if x.get("type") == "thread.started"]
        if len(ids) != 1 or not any(x.get("type") == "turn.completed" for x in events):
            raise NativeRejected("native parent completion unconfirmed")
        sessions = session_root or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "sessions"
        receipt = native_completion(rows(own_rollout(sessions, ids[0])), role)
        state.update(receipt)
        state["status"] = "SUCCEEDED"
        state["parent_id_sha256"] = hashlib.sha256(ids[0].encode()).hexdigest()
        return state
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
