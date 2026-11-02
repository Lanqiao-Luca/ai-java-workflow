"""Controlled gate tests; mocked dispatch is not native/model/Spring execution evidence."""
from pathlib import Path
from unittest.mock import patch
import importlib.util
import json
import tempfile
import unittest

try:
    from tools.native_flow import NativeFlow, FlowRejected, candidate, candidate_evidence_gate, digest, load_definition, snapshot, stage_gate
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from native_flow import NativeFlow, FlowRejected, candidate, candidate_evidence_gate, digest, load_definition, snapshot, stage_gate


def make_catalog(root, stages=None):
    stages = stages or [('requirements', [], ['requirements.md'], False, False),
                        ('implementation', ['requirements'], ['app/src/Generated.java'], False, False),
                        ('review', ['implementation'], ['review.md'], True, False)]
    files = {'agents/example.md': b'Independent controlled test contract.'}
    nodes = []
    for name, deps, writes, preserve, validate in stages:
        path = 'workflows/' + name + '.json'
        nodes.append({'id': name, 'depends_on': deps, 'workflow': path})
        files[path] = json.dumps({'kind': 'native_workflow', 'role': 'workflow_' + name,
                                 'agents': ['agents/example.md'], 'writes': writes,
                                 'task': 'Synthetic protocol only.', 'preserve_candidate': preserve,
                                 'validate': validate}).encode()
    graph = {'kind': 'native_graph', 'graph_id': 'controlled', 'max_parallel': 2, 'nodes': nodes}
    files['graphs/example.json'] = json.dumps(graph).encode()
    files['public-manifest.json'] = json.dumps({'files': [
        {'path': n, 'status': 'reviewed_candidate'} for n in [*files, 'public-manifest.json']]}).encode()
    for name, content in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
    return root / 'graphs/example.json'


class GateTests(unittest.TestCase):
    def test_exact_product_and_completion_accepted(self):
        before = {'task.md': {'sha256': 'a'}}
        after = {**before, 'requirements.md': {'sha256': 'b'}}
        stage_gate(before, after, ['requirements.md'], {'status': 'passed', 'outputs': ['requirements.md']})

    def test_undeclared_mutation_rejected(self):
        with self.assertRaises(FlowRejected):
            stage_gate({'catalog/x': 'a'}, {'catalog/x': 'changed', 'out.md': 'b'}, ['out.md'],
                       {'status': 'passed', 'outputs': ['out.md']})

    def test_missing_and_forged_output_rejected(self):
        for after, result in [({}, {'status': 'passed', 'outputs': ['out.md']}),
                              ({'out.md': 'b'}, {'status': 'passed', 'outputs': []})]:
            with self.assertRaises(FlowRejected):
                stage_gate({}, after, ['out.md'], result)

    def test_frozen_candidate_cannot_be_a_declared_review_output(self):
        with self.assertRaises(FlowRejected):
            stage_gate({}, {'app/src/Code.java': 'b'}, ['app/src/Code.java'],
                       {'status': 'passed', 'outputs': ['app/src/Code.java']}, True)

    def test_linked_product_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'file').write_text('synthetic')
            (root / 'alias').symlink_to(root / 'file')
            with self.assertRaises(FlowRejected): snapshot(root)

    def test_reserved_and_escaped_output_rejected(self):
        for name in ['../out', '/out', 'catalog/out', '.hidden']:
            with self.assertRaises(FlowRejected):
                stage_gate({}, {name: 'b'}, [name], {'status': 'passed', 'outputs': [name]})

    def test_cycle_and_unknown_dependency_rejected(self):
        for deps in [['a'], ['missing']]:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                path = make_catalog(root, [('a', deps, ['a.md'], False, False)])
                with self.assertRaises(FlowRejected): load_definition(path, root)

    def test_concurrent_write_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = make_catalog(root, [('a', [], ['same.md'], False, False),
                                       ('b', [], ['same.md'], False, False)])
            with self.assertRaises(FlowRejected): load_definition(path, root)

    def test_run_root_inside_catalog_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = make_catalog(root)
            with self.assertRaises(FlowRejected):
                NativeFlow({'task.md': b'Synthetic'}, root, path, root / 'private')

    def _run(self, fail=False, invalid_validation=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / 'catalog'
            stages = None
            if invalid_validation:
                stages = [('verification', [], ['verification.md'], True, True),
                          ('delivery', ['verification'], ['delivery.md'], True, False)]
            path = make_catalog(catalog, stages)
            def prepare(workspace, node, workflow):
                if workflow['preserve_candidate'] and not workflow['validate']:
                    mapping = candidate(workspace)
                    (workspace / 'validation.json').write_text(json.dumps({'status': 'PASSED',
                        'source_sha256': mapping, 'candidate_id': digest(mapping)}))
            flow = NativeFlow({'task.md': b'Synthetic', 'app/pom.xml': b'<project/>'}, catalog,
                              path, root / 'private', prepare=prepare, validate=lambda *args: {'status': 'PASSED',
                              'candidate_id': 'wrong', 'source_sha256': {}})
            calls = []
            def fake(workspace, role, task, private, **kwargs):
                calls.append(role)
                if fail and role == 'workflow_implementation':
                    raise FlowRejected('controlled failure')
                writes = next(w['writes'] for w in flow.workflows.values() if w['role'] == role)
                for name in writes:
                    p = workspace / name
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text('Controlled unit-test product, not a native model artifact.')
                workflow = next(w for w in flow.workflows.values() if w['role'] == role)
                if workflow['preserve_candidate'] or workflow['validate']:
                    for name in writes:
                        if name.endswith('.md'):
                            path = workspace / name
                            path.write_text('candidate_id: ' + digest(candidate(workspace)) + '\n' + path.read_text())
                return {'status': 'SUCCEEDED', 'result': {'status': 'passed', 'outputs': writes}}
            # Replace the dispatch seam only in this explicitly mocked unit test.
            module = NativeFlow.__module__
            with patch(module + '.dispatch', side_effect=fake):
                result = flow.run()
            return result, calls

    def test_actual_fixture_worktrees_and_promotion_with_mocked_roles(self):
        result, calls = self._run()
        self.assertEqual(result['status'], 'SUCCEEDED')
        self.assertEqual(calls, ['workflow_requirements', 'workflow_implementation', 'workflow_review'])
        self.assertIn('app/src/Generated.java', result['products_sha256'])

    def test_failed_node_blocks_descendants(self):
        result, calls = self._run(fail=True)
        self.assertEqual(result['status'], 'FAILED')
        self.assertNotIn('workflow_review', calls)
        self.assertEqual(result['stages']['review']['status'], 'PENDING')

    def test_false_green_host_validation_blocks_delivery(self):
        result, calls = self._run(invalid_validation=True)
        self.assertEqual(result['status'], 'FAILED')
        self.assertNotIn('workflow_delivery', calls)

    def test_parallel_reviewers_share_frozen_candidate_with_mocked_roles(self):
        import threading
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / 'catalog'
            path = make_catalog(catalog, [('a', [], ['a.md'], True, False),
                                          ('b', [], ['b.md'], True, False)])
            def prepare(workspace, node, workflow):
                mapping = candidate(workspace)
                (workspace / 'validation.json').write_text(json.dumps({'status': 'PASSED',
                    'source_sha256': mapping, 'candidate_id': digest(mapping)}))
            flow = NativeFlow({'task.md': b'Synthetic', 'app/pom.xml': b'<project/>'}, catalog,
                              path, root / 'private', prepare=prepare)
            barrier = threading.Barrier(2, timeout=5)
            ids = []
            def fake(workspace, role, task, private, **kwargs):
                ids.append(digest(candidate(workspace)))
                barrier.wait()
                name = role.rsplit('_', 1)[1] + '.md'
                (workspace / name).write_text('candidate_id: ' + digest(candidate(workspace)) + '\nControlled reviewer product.')
                return {'status': 'SUCCEEDED', 'result': {'status': 'passed', 'outputs': [name]}}
            with patch(NativeFlow.__module__ + '.dispatch', side_effect=fake):
                result = flow.run()
            self.assertEqual(result['status'], 'SUCCEEDED')
            self.assertEqual(len(set(ids)), 1)
            a, b = result['stages']['a'], result['stages']['b']
            self.assertLess(max(a['started'], b['started']), min(a['ended'], b['ended']))

    def test_document_claim_must_match_current_candidate(self):
        for header in ['', 'candidate_id: ' + '0' * 64, 'candidate_id: stale-v1']:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / 'app').mkdir()
                (root / 'app/pom.xml').write_text('<project/>')
                mapping = candidate(root)
                evidence = {'status': 'PASSED', 'source_sha256': mapping, 'candidate_id': digest(mapping)}
                (root / 'review.md').write_text(header + '\nReview of candidate.')
                with self.assertRaises(FlowRejected):
                    candidate_evidence_gate(root, ['review.md'], evidence)

    def test_correct_header_cannot_cover_stale_host_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app').mkdir()
            (root / 'app/pom.xml').write_text('<project/>')
            old = candidate(root)
            evidence = {'status': 'PASSED', 'source_sha256': old, 'candidate_id': digest(old)}
            (root / 'app/pom.xml').write_text('<project>new</project>')
            (root / 'review.md').write_text('candidate_id: ' + digest(candidate(root)) + '\nReview.')
            (root / 'validation.json').write_text(json.dumps(evidence))
            with self.assertRaises(FlowRejected):
                candidate_evidence_gate(root, ['review.md'])

    def test_missing_or_failed_host_validation_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(FlowRejected):
                candidate_evidence_gate(root, [])
            (root / 'validation.json').write_text(json.dumps({'status': 'FAILED', 'source_sha256': {}, 'candidate_id': digest({})}))
            with self.assertRaises(FlowRejected):
                candidate_evidence_gate(root, [])

    def test_current_document_and_current_evidence_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app').mkdir()
            (root / 'app/pom.xml').write_text('<project/>')
            mapping = candidate(root)
            (root / 'review.md').write_text('candidate_id: ' + digest(mapping) + '\nReview.')
            (root / 'validation.json').write_text(json.dumps({'status': 'PASSED', 'source_sha256': mapping, 'candidate_id': digest(mapping)}))
            self.assertEqual(candidate_evidence_gate(root, ['review.md']), digest(mapping))


if __name__ == '__main__':
    unittest.main()
