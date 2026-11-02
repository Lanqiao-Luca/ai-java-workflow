"""Offline protocol fixtures, not evidence of model or native Agent execution."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest

from tools.native_agents import NativeRejected, dispatch, native_completion, own_rollout, rows


def fixture(role="workflow_probe"):
    def call(name, args, ident):
        return {"type": "response_item", "payload": {"type": "function_call", "namespace": "collaboration",
                "name": name, "call_id": ident, "arguments": json.dumps(args)}}
    def output(data, ident):
        return {"type": "response_item", "payload": {"type": "function_call_output",
                "call_id": ident, "output": json.dumps(data)}}
    result = json.dumps({"status": "passed", "summary": "synthetic fixture", "outputs": []})
    return [call("spawn_agent", {"agent_type": role, "fork_turns": "none"}, "spawn"),
            output({"task_name": "/root/stage"}, "spawn"), call("list_agents", {}, "list"),
            output({"agents": [{"agent_name": "/root/stage", "agent_status": {"completed": result}}]}, "list")]


class NativeProtocolTests(unittest.TestCase):
    def test_native_call_and_completion_pair(self):
        receipt = native_completion(fixture(), "workflow_probe")
        self.assertTrue(receipt["native_completed"])
        self.assertEqual(receipt["spawn_calls"], 1)

    def test_parent_success_without_native_call_rejected(self):
        with self.assertRaises(NativeRejected):
            native_completion([{"type": "agent_message", "text": "success"}], "workflow_probe")

    def test_wrong_role_rejected(self):
        with self.assertRaises(NativeRejected):
            native_completion(fixture("default"), "workflow_probe")

    def test_missing_tool_output_rejected(self):
        with self.assertRaises(NativeRejected):
            native_completion(fixture()[:-1], "workflow_probe")

    def test_wrong_child_identity_rejected(self):
        data = fixture()
        data[1]["payload"]["output"] = json.dumps({"task_name": "/root/other"})
        with self.assertRaises(NativeRejected):
            native_completion(data, "workflow_probe")

    def test_failed_spawn_rejected(self):
        data = fixture()
        data[1]["payload"]["output"] = json.dumps({"error": "synthetic unavailable role"})
        with self.assertRaises(NativeRejected):
            native_completion(data, "workflow_probe")

    def test_parent_shell_call_rejected(self):
        data = fixture()
        data.insert(0, {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec"}})
        with self.assertRaises(NativeRejected):
            native_completion(data, "workflow_probe")

    def test_parent_web_tool_cannot_hide_beside_valid_spawn(self):
        data = fixture()
        data.append({"type": "response_item", "payload": {"type": "web_search_call"}})
        with self.assertRaises(NativeRejected):
            native_completion(data, "workflow_probe")

    def test_inherited_context_rejected(self):
        data = fixture()
        data[0]["payload"]["arguments"] = json.dumps({"agent_type": "workflow_probe", "fork_turns": "all"})
        with self.assertRaises(NativeRejected):
            native_completion(data, "workflow_probe")

    def test_child_failure_and_unstructured_success_rejected(self):
        for result in ["passed", json.dumps({"status": "failed", "summary": "failure", "outputs": []})]:
            data = fixture()
            data[3]["payload"]["output"] = json.dumps({"agents": [{"agent_name": "/root/stage",
                                                   "agent_status": {"completed": result}}]})
            with self.assertRaises(NativeRejected):
                native_completion(data, "workflow_probe")

    def test_duplicate_native_calls_rejected(self):
        data = fixture()
        data.extend(deepcopy(fixture()))
        with self.assertRaises(NativeRejected):
            native_completion(data, "workflow_probe")

    def test_log_link_and_size_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "protocol.jsonl"
            path.write_text("{}\n")
            link = Path(temp) / "link"
            link.symlink_to(path)
            for file, limit in [(link, 100), (path, 1)]:
                with self.assertRaises(NativeRejected):
                    rows(file, limit)

    def test_only_exact_uuid_session_lookup(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(NativeRejected):
                own_rollout(temp, "../../unrelated")
            with self.assertRaises(NativeRejected):
                own_rollout(temp, "00000000-0000-7000-8000-000000000001")

    def test_private_path_alias_rejected_before_workspace_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / "workspace"
            workspace.mkdir()
            alias = root / "alias"
            alias.symlink_to(workspace, target_is_directory=True)
            with self.assertRaises(NativeRejected):
                dispatch(workspace, "workflow_probe", "synthetic", alias / "new-private")
            self.assertFalse((workspace / "new-private").exists())


if __name__ == "__main__":
    unittest.main()
