"""Byte manifests for explicitly prepared public build caches; never discover HOME."""
from pathlib import Path
import hashlib
import json
from .runtime import Rejected, identity

MARKER = 'public-build-cache.json'

def files(root):
    root = Path(root).resolve(strict=True)
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink(): raise Rejected('cache symlink refused')
        if p.is_file() and p != root / MARKER:
            name = p.relative_to(root).as_posix()
            if p.name in {'settings.xml','settings-security.xml','gradle.properties'} or 'init.d' in p.relative_to(root).parts:
                raise Rejected('ambient build configuration refused')
            result[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result

def seal(root, tool):
    hashes = files(root)
    record = {'kind':'explicit_public_build_cache','tool':tool,'source':'https://repo.maven.apache.org/maven2',
              'files':hashes,'cache_id':identity(hashes)}
    (Path(root)/MARKER).write_text(json.dumps(record,indent=2)+'\n')
    return {'tool':tool,'cache_id':record['cache_id'],'file_count':len(hashes)}

def verify(root, tool):
    record = json.loads((Path(root)/MARKER).read_text())
    hashes = files(root)
    if (record.get('kind')!='explicit_public_build_cache' or record.get('tool')!=tool
            or record.get('source')!='https://repo.maven.apache.org/maven2'
            or record.get('files')!=hashes or record.get('cache_id')!=identity(hashes)):
        raise Rejected('cache admission identity mismatch')
    return record['cache_id']
