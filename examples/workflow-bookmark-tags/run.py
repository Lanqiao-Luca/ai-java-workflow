"""Run red/green Spring tests with isolated Maven settings and temporary outputs.
Only public Maven Central artifacts are downloaded; no application service is contacted.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
EXPECTED = {"contextWiresRealServiceAndController", "normalizeDeduplicateAndPersist",
            "emptyListClearsTags", "nullListRejectsWithoutMutation", "blankItemRejectsWholeRequest",
            "nullItemRejectsWholeRequest", "nonOwnerRejectsBeforeTagValidation",
            "staleVersionRejectsWithoutMutation", "missingVersionRejects", "missingReferenceRejects",
            "normalizedNoopPreservesVersionAndAudit", "repeatAtCurrentVersionIsNoop",
            "staleRetryAfterSuccessRejects"}
GAPS = {"blankItemRejectsWholeRequest", "nullItemRejectsWholeRequest"}

def source_id():
    names = [p for p in sorted((ROOT / "app").rglob("*")) if p.is_file()]
    names += [ROOT / "fixtures/TagService-v1.java", ROOT / "run.py"]
    pairs = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in names}
    return hashlib.sha256(json.dumps(pairs, sort_keys=True).encode()).hexdigest(), pairs

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=300, help="Per-Maven-attempt deadline in seconds")
    parser.add_argument("--java-home", type=Path)
    parser.add_argument("--maven-home", type=Path)
    parser.add_argument("--output", type=Path, help="Optional sanitized result JSON outside the case")
    args = parser.parse_args()
    if os.name != "posix" or args.timeout <= 0:
        print("NOT_RUN: POSIX process isolation and a positive deadline required"); return 2
    if args.output and args.output.resolve().is_relative_to(ROOT):
        raise SystemExit("Refusing to write runtime output into immutable case; choose an external path")
    manifest = json.loads((ROOT / "artifact-manifest.json").read_text())["files"]
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file()}
    if any(p.is_symlink() for p in ROOT.rglob("*")):
        raise SystemExit("FAIL: symlinks not supported")
    declared = {row["path"] for row in manifest}
    if declared != actual - {"artifact-manifest.json"} or len(declared) != len(manifest):
        raise SystemExit("FAIL: case file set drift")
    for row in manifest:
        target = (ROOT / row["path"]).resolve()
        if not target.is_relative_to(ROOT) or hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]:
            raise SystemExit("FAIL: source identity drift")
    env = {k: v for k, v in os.environ.items() if k not in {
        "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH",
        "MAVEN_OPTS", "MAVEN_ARGS", "MAVEN_EXT_CLASS_PATH", "MAVEN_PROJECTBASEDIR", "MAVEN_CONFIG", "JAVA_OPTS"}}
    env["MAVEN_SKIP_RC"] = "true"
    if args.java_home: env["JAVA_HOME"] = str(args.java_home.resolve())
    java = Path(env["JAVA_HOME"]) / "bin/java" if env.get("JAVA_HOME") else shutil.which("java")
    maven = args.maven_home.resolve() / "bin/mvn" if args.maven_home else shutil.which("mvn")
    if not java or not maven:
        print("NOT_RUN: JDK17+ and Maven3.6.3+ required"); return 2
    probe = subprocess.run([str(java), "-version"], env=env, capture_output=True, text=True)
    if probe.returncode:
        print("NOT_RUN: no usable JDK"); return 2
    identity, sources = source_id()
    report = {"synthetic": True, "source_bundle_id": identity, "source_sha256": sources,
              "scope": "Real Spring Boot context and MockMvc request tests; no live server or production auth",
              "java": probe.stderr.strip().splitlines()[0], "variants": []}
    with tempfile.TemporaryDirectory(prefix="java-workflow-") as temporary:
        temp = Path(temporary)
        settings = temp / "settings.xml"
        settings.write_text('<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0"><mirrors><mirror><id>public-central-only</id><mirrorOf>*</mirrorOf><url>https://repo.maven.apache.org/maven2</url></mirror></mirrors></settings>')
        for variant in ["v1", "v2"]:
            app = temp / variant
            shutil.copytree(ROOT / "app", app)
            if variant == "v1":
                shutil.copyfile(ROOT / "fixtures/TagService-v1.java", app / "src/main/java/example/workflow/TagService.java")
            compiled_sources = {p.relative_to(app).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(app.rglob("*")) if p.is_file()}
            candidate_id = hashlib.sha256(json.dumps(compiled_sources, sort_keys=True).encode()).hexdigest()
            command = [str(maven), "--batch-mode", "--no-transfer-progress", "--settings", str(settings),
                       "--global-settings", str(settings), "-Dmaven.repo.local=" + str(temp / "repository"),
                       "-Duser.home=" + str(temp / "home"), "-Dstyle.color=never", "-f", str(app / "pom.xml"), "test"]
            process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, start_new_session=True, cwd=app)
            try:
                stdout, stderr = process.communicate(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                report["status"] = "TIMEOUT"
                if args.output: args.output.write_text(json.dumps(report, indent=2) + "\n")
                print("FAIL: Maven deadline reached; process group stopped, no automatic retry")
                return 1
            result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            xmls = list((app / "target/surefire-reports").glob("TEST-*.xml"))
            seen, failed, skipped, errors = [], [], [], []
            for xml in xmls:
                suite = ET.parse(xml).getroot()
                for item in suite.findall("testcase"):
                    name = item.attrib["name"]; seen.append(name)
                    if item.find("failure") is not None: failed.append(name)
                    if item.find("error") is not None: errors.append(name)
                    if item.find("skipped") is not None: skipped.append(name)
            expected_failures = GAPS if variant == "v1" else set()
            accepted = (result.returncode == (1 if variant == "v1" else 0)
                        and len(seen) == len(EXPECTED) and set(seen) == EXPECTED
                        and set(failed) == expected_failures and len(failed) == len(expected_failures)
                        and not errors and not skipped)
            report["variants"].append({"variant": variant, "candidate_id": candidate_id, "compiled_source_sha256": compiled_sources, "process_exit": result.returncode,
                                       "tests": len(seen), "failures": sorted(failed), "errors": errors,
                                       "skipped": skipped, "test_names": sorted(seen), "accepted": accepted})
            print(variant + ": tests=" + str(len(seen)) + ", failures=" + str(len(failed)) + ", accepted=" + str(accepted))
            if not accepted:
                report["status"] = "FAILED"
                if args.output: args.output.write_text(json.dumps(report, indent=2) + "\n")
                print("FAIL: unexpected build or test results; raw build logs are not publication evidence")
                # Keep machine-local paths and environment-dependent logs out of published evidence.
                print("Failure category: build/test result mismatch; machine-local Maven logs are suppressed")
                return 1
    report["candidate_id"] = report["variants"][-1]["candidate_id"]
    report["status"] = "PASSED"
    if args.output: args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: real Spring red/green checks; 13 tests, two specified v1 failures, all v2 pass")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
