"""Offline Java contract runner; no install, network or project build outputs."""
from pathlib import Path
import re
import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
EXPECTED = {"trim", "blank", "empty", "null", "owner", "owner-before-title",
            "stale", "preserved-fields-and-audit", "normalized-noop", "plain-noop",
            "missing", "stale-after-success"}

def main():
    rows = json.loads((ROOT / "artifact-manifest.json").read_text())["files"]
    expected_files = {"task.json", "before/BookmarkService.java", "after/BookmarkService.java",
                      "tests/BookmarkServiceTest.java", "run.py", "change.diff"}
    if len(rows) != len(expected_files) or {row["path"] for row in rows} != expected_files:
        print("FAIL: source identity set mismatch; refresh reviewed case artifacts")
        return 1
    for row in rows:
        if hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            print("FAIL: source identity drift; review changes before refreshing evidence")
            return 1
    # Do not implicitly load JVM agents/options or classpaths from the host environment.
    java_env = {k: v for k, v in os.environ.items()
                if k not in {"JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH"}}
    if not shutil.which("javac") or not shutil.which("java"):
        print("NOT_RUN: local JDK 17+ required")
        return 2
    for command in ["javac", "java"]:
        probe = subprocess.run([command, "-version"], capture_output=True, text=True, env=java_env)
        if probe.returncode:
            print("NOT_RUN: Java launcher exists without a usable runtime")
            return 2
    for variant in ["before", "after"]:
        with tempfile.TemporaryDirectory(prefix="bookmark-contract-") as output:
            compile_result = subprocess.run([
                "javac", "--release", "17", "-d", output,
                str(ROOT / variant / "BookmarkService.java"),
                str(ROOT / "tests/BookmarkServiceTest.java")], capture_output=True, text=True, env=java_env)
            if compile_result.returncode:
                print("COMPILE_FAILED: " + variant)
                print(compile_result.stderr)
                return 1
            result = subprocess.run(["java", "-cp", output, "BookmarkServiceTest"],
                                    capture_output=True, text=True, env=java_env)
            print(variant.upper())
            print(result.stdout, end="")
            pass_ids = re.findall(r"^PASS ([\w-]+)$", result.stdout, re.MULTILINE)
            fail_ids = re.findall(r"^FAIL ([\w-]+) ", result.stdout, re.MULTILINE)
            passes, fails = set(pass_ids), set(fail_ids)
            expected_failures = {"trim", "blank", "empty", "normalized-noop"} if variant == "before" else set()
            expected_code = result.returncode == (1 if variant == "before" else 0)
            summary = "SUMMARY passed=8 failed=4" if variant == "before" else "SUMMARY passed=12 failed=0"
            summaries = re.findall(r"^SUMMARY .*", result.stdout, re.MULTILINE)
            expected_failure = ("java.lang.AssertionError: contract tests failed" in result.stderr
                                if variant == "before" else True)
            if (fails != expected_failures or passes != EXPECTED - expected_failures
                    or len(pass_ids) != len(passes) or len(fail_ids) != len(fails)
                    or summaries != [summary] or not expected_code or not expected_failure):
                print("FAIL: unexpected contract results")
                print(result.stderr)
                return 1
    print("PASS: baseline exposes 4 specified gaps; candidate satisfies all 12 checks")
    return 0

if __name__ == "__main__":
    sys.exit(main())
