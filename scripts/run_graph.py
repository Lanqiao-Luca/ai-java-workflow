"""Explicit local Graph execution; never runs a model, pushes Git or installs tools."""
from pathlib import Path
import argparse
import json
import os
import signal
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--definition", type=Path)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--java-home", type=Path)
    parser.add_argument("--host-capacity", type=int)
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--inspect", type=Path, help="Audit an interrupted checkpoint; never replay unknown commands")
    parser.add_argument("--cancel", type=Path, help="Request cancellation from the live owner, no stale-PID signals")
    args = parser.parse_args()
    if os.name != "posix":
        print("NOT_RUN: POSIX host required; no bare-process fallback"); return 2
    sys.path.insert(0, str(ROOT))
    from tools.execution.catalog import load_definition
    from tools.execution.runtime import GraphRun, Rejected, inspect_interrupted, token
    current = None
    try:
        if args.inspect and args.cancel: raise Rejected("choose one control action")
        if args.inspect:
            print(json.dumps(inspect_interrupted(args.inspect), indent=2)); return 0
        if args.cancel:
            directory = args.cancel.resolve(strict=True)
            state = json.loads((directory / "state.json").read_text())
            if state["graph_id"] != directory.name or not (directory / "owner.lock").is_file():
                raise Rejected("unrecognized execution checkpoint")
            (directory / "cancel.flag").write_text("explicit cancellation request\n")
            print("CANCEL_REQUESTED: live owner will stop groups; no automatic cleanup"); return 0
        if not args.definition or not args.repo or not args.runtime_root:
            parser.error("--definition, --repo and --runtime-root are required for execution")
        definition, catalog = load_definition(args.definition, ROOT)
        if args.run_id: definition["graph_id"] = token(args.run_id)
        roots = [args.java_home.resolve(strict=True)] if args.java_home else []
        current = GraphRun(args.repo, args.base, args.runtime_root, definition,
                           tool_roots=roots, java_home=args.java_home, host_capacity=args.host_capacity)
        signal.signal(signal.SIGTERM, lambda *_: current.cancel.set())
        signal.signal(signal.SIGINT, lambda *_: current.cancel.set())
        state = current.run()
        state["catalog_id"] = catalog["catalog_id"]
        current._save()
        if args.cleanup: current.cleanup()
        print(json.dumps(state, indent=2))
        return 0 if state["status"] == "SUCCEEDED" else 1
    except Rejected:
        print("REJECTED: snapshot, resource or sandbox admission failed; no implicit fallback")
        return 2
    except Exception:
        print("FAILED: execution did not produce a verified result; local checkpoint retained")
        return 1
    finally:
        if current: current.close()


if __name__ == "__main__":
    raise SystemExit(main())
