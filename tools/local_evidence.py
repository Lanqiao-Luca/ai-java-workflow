"""Read only explicitly listed public files and assess their bounded coverage.

POSIX directory descriptors and O_NOFOLLOW prevent following a substituted link.
The supplied allowlist expresses caller scope; it is not an authorization service.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import stat
from tools.evidence_coverage import assess


class LocalEvidenceError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise LocalEvidenceError(message)


def validate_spec(spec):
    keys = {'source_id', 'needle', 'mode', 'probe_id', 'max_pages', 'max_bytes', 'max_total_bytes', 'files'}
    need(isinstance(spec, dict) and set(spec) == keys, 'file scope fields')
    for key in ('source_id', 'needle', 'probe_id'):
        need(isinstance(spec[key], str) and bool(spec[key].strip()), 'source context')
    need(isinstance(spec['mode'], str) and spec['mode'] in {'sample', 'complete'}, 'mode')
    for key, maximum in (('max_pages', 100), ('max_bytes', 65536), ('max_total_bytes', 262144)):
        need(type(spec[key]) is int and 0 < spec[key] <= maximum, 'bounded read budget')
    need(isinstance(spec['files'], list) and 0 < len(spec['files']) <= 100, 'explicit file set')
    seen = set()
    for item in spec['files']:
        need(isinstance(item, dict) and set(item) == {'path', 'sha256'}, 'file identity fields')
        name = item['path']
        need(isinstance(name, str) and bool(name) and not any(c in name for c in '\\\x00\n\r:*?[]'), 'relative file path')
        p = PurePosixPath(name)
        need(not p.is_absolute() and p.as_posix() == name
             and all(part and not part.startswith('.') for part in name.split('/')), 'unsafe file path')
        need(name not in seen, 'duplicate file')
        need(isinstance(item['sha256'], str) and re.fullmatch('[a-f0-9]{64}', item['sha256']) is not None, 'file digest')
        seen.add(name)


def _open_relative(root_fd, name):
    directory = os.dup(root_fd)
    try:
        parts = name.split('/')
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = next_fd
        # Nonblocking avoids hanging on FIFO; fstat rejects every nonregular file.
        return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)


def collect(root, spec):
    validate_spec(spec)
    need(os.name == 'posix' and hasattr(os, 'O_NOFOLLOW'), 'POSIX no-follow support required')
    root = Path(root)
    need(root.is_absolute() and root == root.resolve() and root.is_dir(), 'canonical approved root required')
    snapshot = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    scope = {k: spec[k] for k in ('source_id', 'needle', 'mode', 'probe_id', 'max_pages')}
    scope['snapshot'] = snapshot
    pages, originals, used = [], [], 0

    def result(status=None, reason=None):
        coverage = assess(scope, pages)
        if status:
            coverage.update(status=status, coverage_complete=False, absence='unknown')
        return {'coverage': coverage, 'reason': reason, 'originals': originals,
                'bytes_read': used, 'source_requests': 0, 'scope': 'explicit_file_set_only',
                'pages': pages}

    try:
        root_fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except PermissionError:
        return result('DENIED', 'root permission')
    except OSError:
        return result('UNKNOWN', 'root unavailable')
    try:
        for index, item in enumerate(spec['files'][:spec['max_pages']]):
            try:
                fd = _open_relative(root_fd, item['path'])
                try:
                    before = os.fstat(fd)
                    if not stat.S_ISREG(before.st_mode):
                        return result('REJECTED', 'not a regular file')
                    limit = min(spec['max_bytes'], spec['max_total_bytes'] - used)
                    if before.st_size > limit:
                        return result('PARTIAL', 'byte budget')
                    raw = b''
                    while len(raw) <= limit:
                        block = os.read(fd, min(16384, limit + 1 - len(raw)))
                        if not block:
                            break
                        raw += block
                    used += len(raw)
                    after = os.fstat(fd)
                finally:
                    os.close(fd)
            except PermissionError:
                return result('DENIED', 'file permission')
            except FileNotFoundError:
                return result('UNKNOWN', 'listed file missing')
            except OSError:
                return result('REJECTED', 'link, directory or unavailable file')
            if len(raw) > limit:
                return result('PARTIAL', 'byte budget changed during read')
            stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            actual_sha = hashlib.sha256(raw).hexdigest()
            if stamp(before) != stamp(after) or actual_sha != item['sha256']:
                return result('STALE', 'listed bytes changed')
            try:
                content = raw.decode('utf-8')
            except UnicodeDecodeError:
                return result('REJECTED', 'UTF-8 text required')
            if '\x00' in content:
                return result('REJECTED', 'binary content')
            originals.append({'path': item['path'], 'sha256': actual_sha, 'bytes': len(raw)})
            page = {k: scope[k] for k in ('source_id', 'snapshot', 'needle')}
            page.update(cursor_in=None if index == 0 else item['path'],
                        cursor_out=None if index + 1 == len(spec['files']) else spec['files'][index + 1]['path'],
                        finished=index + 1 == len(spec['files']), truncated=False, status='OK',
                        rows=[{'id': item['path'] + ':' + str(n), 'text': line}
                              for n, line in enumerate(content.splitlines(), 1) if line])
            pages.append(page)
            coverage = assess(scope, pages)
            if coverage['status'] in {'SAMPLE_FOUND', 'SAMPLE_NOT_FOUND', 'COMPLETE_MATCH', 'COMPLETE_EMPTY', 'UNRESOLVED_EMPTY'}:
                return result()
        return result()
    finally:
        os.close(root_fd)
