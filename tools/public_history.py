"""Resolve preserved public method bytes for historical receipts only."""
from pathlib import Path
import hashlib
import json

INDEX_SHA256 = '4dbd1e96136a136686208162d80d3b5453249e01758536bdc1047be3ca48bdec'


def source_bytes(root, name):
    root = Path(root).resolve()
    index = root / 'docs/public-baseline/sources.json'
    raw = index.read_bytes()
    if hashlib.sha256(raw).hexdigest() != INDEX_SHA256:
        raise ValueError('historical public source index drift')
    rows = json.loads(raw)['sources']
    if name in rows:
        row = rows[name]
        source = root / row['path']
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError('unsafe historical source path')
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('historical public source bytes drift')
        return data
    source = root / name
    if source.is_symlink() or not source.resolve().is_relative_to(root):
        raise ValueError('unsafe current source path')
    return source.read_bytes()
