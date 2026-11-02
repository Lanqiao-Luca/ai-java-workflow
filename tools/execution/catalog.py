"""Bind a public Graph definition to concrete Workflow command contracts."""
from pathlib import Path
import hashlib
import json
from .runtime import Rejected, identity, relative, validate


def load_definition(path, root):
    root = Path(root).resolve(strict=True)
    path = Path(path).resolve(strict=True)
    if path.parent != root / "graphs" or path.suffix != ".json":
        raise Rejected("Graph definition must be a catalog graphs/*.json file")
    data = json.loads(path.read_text())
    if set(data) != {"kind", "graph_id", "max_parallel", "nodes"} or data["kind"] != "graph_definition":
        raise Rejected("unsupported Graph definition")
    hashes = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()}
    def source(name):
        relative(name)
        file = (root / name).resolve(strict=True)
        if not file.is_relative_to(root) or not file.is_file(): raise Rejected("catalog reference outside root")
        hashes[name] = hashlib.sha256(file.read_bytes()).hexdigest()
        return file
    nodes = []
    for item in data["nodes"]:
        if set(item) != {"id", "depends_on", "workflow"}: raise Rejected("unexpected Graph node fields")
        file = source(item["workflow"])
        if file.parent != root / "workflows" or file.suffix != ".json":
            raise Rejected("invalid Workflow definition reference")
        workflow = json.loads(file.read_text())
        if (set(workflow) != {"kind", "agent", "skills", "command", "allowed_write", "success_pattern", "timeout"}
                or workflow["kind"] != "workflow_definition"):
            raise Rejected("unsupported Workflow definition")
        agent = source(workflow["agent"])
        if agent.parent != root / "agents" or agent.suffix != ".md": raise Rejected("invalid Agent")
        if not isinstance(workflow["skills"], list) or not workflow["skills"]:
            raise Rejected("Workflow skills required")
        for name in workflow["skills"]:
            skill = source(name)
            if not skill.is_relative_to(root / "skills") or skill.name != "SKILL.md": raise Rejected("invalid Skill")
        nodes.append({"id": item["id"], "depends_on": item["depends_on"],
                      **{key: workflow[key] for key in ["command", "allowed_write", "success_pattern", "timeout"]}})
    definition = {"graph_id": data["graph_id"], "max_parallel": data["max_parallel"], "nodes": nodes}
    validate(definition)
    return definition, {"catalog_id": identity(hashes), "source_sha256": hashes}
