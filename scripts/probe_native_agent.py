"""Opt-in real native Agent probe. Synthetic input; private logs outside this repository."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import uuid
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.native_agents import dispatch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    if run_root.exists() or run_root.is_relative_to(ROOT):
        parser.error("use a new private run root outside the repository")
    run_root.mkdir(parents=True, mode=0o700)
    workspace = run_root / "workspace"
    agents = workspace / ".codex/agents"
    agents.mkdir(parents=True)
    instructions = ("Read task.txt in this synthetic workspace. Do not edit files, use Git, "
                    "or access unrelated directories. Return only the JSON requested by the caller.")
    (agents / "workflow_probe.toml").write_text(
        'name = "workflow_probe"\ndescription = "Synthetic native dispatch probe."\n'
        'developer_instructions = ' + json.dumps(instructions) + "\n")
    marker = "SYNTHETIC_" + uuid.uuid4().hex
    (workspace / "task.txt").write_text(marker + "\n")
    result = dispatch(workspace, "workflow_probe",
                      "Read task.txt. Return status passed, summary exactly the stripped file content, "
                      "and outputs an empty array. No file changes or Git operations.",
                      run_root / "private", codex=args.codex, timeout=args.timeout)
    if result["result"]["summary"] != marker:
        raise ValueError("native child did not return the actual synthetic input")
    result["scope"] = "real native spawn and completion; not a Java/Spring workflow test"
    result["source_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ["tools/native_agents.py", "scripts/probe_native_agent.py"]}
    (run_root / "probe-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
