"""Run the eight offline repository checks, stopping at the first failure."""
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    "check.py", "check_agent_cases.py", "check_workflow_cases.py",
    "check_graph_cases.py", "check_spring_build_cases.py", "check_docker_cases.py",
    "check_native_cases.py", "check_loop_cases.py",
)


def run_checks(root=ROOT, checks=CHECKS):
    """Internal runner; root/checks must come from trusted code, not user input."""
    for index, name in enumerate(checks, 1):
        print(f"[{index}/{len(checks)}] {name}", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, "-B", str(root / "scripts" / name)],
                cwd=root, timeout=60,
            )
        except subprocess.TimeoutExpired:
            print(f"FAIL: {name} exceeded 60 seconds; remaining checks not run", flush=True)
            return 124
        except OSError:
            print(f"FAIL: could not start {name}; remaining checks not run", flush=True)
            return 2
        if result.returncode:
            print(f"FAIL: {name} exited {result.returncode}; remaining checks not run", flush=True)
            return result.returncode if result.returncode > 0 else 128 - result.returncode
    print(f"PASS: {len(checks)} offline checks; no model, Java build or Docker invoked", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run_checks())
    except KeyboardInterrupt:
        print("\nSTOP: interrupted; remaining checks not run", flush=True)
        sys.exit(130)
