"""Read-only Markdown declarations and preserved archive checks; no semantic verdict."""
from pathlib import Path
import hashlib
import json
import re


class ContractError(ValueError):
    pass


def fields(text):
    """Require declarations before the title, after optional native frontmatter."""
    body = text
    if body.startswith('---\n'):
        end = body.find('\n---\n', 4)
        if end < 0:
            raise ContractError('unclosed frontmatter')
        body = body[end + 5:]
    blocks = [block.strip() for block in re.split(r'\n\s*\n', body.strip())]
    result = {}
    for position, label in enumerate(('目的', '适用于')):
        prefix = '**' + label + '**：'
        if len(blocks) <= position or not blocks[position].startswith(prefix):
            raise ContractError('declaration absent or not before title: ' + label)
        value = blocks[position][len(prefix):].strip()
        if not value or '\n' in value or value in {'待填', '待核', 'UNKNOWN'}:
            raise ContractError('empty or placeholder declaration: ' + label)
        if value in {'将研发经验表达为可复用、可验证的方法。', '将通用规范适配为当前任务可消费的结果。'}:
            raise ContractError('generic declaration must be specific to this file')
        result[label] = value
    return result


def local(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ContractError('invalid document path')
    path = root / name
    if any(part in {'..', '.'} for part in Path(name).parts):
        raise ContractError('unsafe document path')
    if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise ContractError('symlink document path')
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ContractError('missing document')
    return path


def check(root, index_path='docs/document-contract-index.json'):
    root = Path(root).resolve()
    data = json.loads(local(root, index_path).read_text())
    if data.get('version') != 1 or not isinstance(data.get('documents'), dict):
        raise ContractError('invalid document index')
    rows = data['documents']
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*.md')
              if '.git' not in p.relative_to(root).parts}
    if set(rows) != actual:
        raise ContractError('document coverage drift')
    counts = {'current': 0, 'preserved': 0}
    for name, row in rows.items():
        path = local(root, name)
        mode = row.get('mode')
        if mode == 'current':
            if set(row) != {'mode'}:
                raise ContractError('current declaration must be maintained in document')
            fields(path.read_text())
        elif mode == 'preserved':
            if set(row) != {'mode', 'sha256', 'purpose', 'applies_to', 'reason'}:
                raise ContractError('incomplete archive sidecar')
            if any(not isinstance(row[k], str) or not row[k].strip()
                   for k in ('purpose', 'applies_to', 'reason')):
                raise ContractError('archive purpose or reason absent')
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise ContractError('preserved document bytes drift')
        else:
            raise ContractError('unknown document mode')
        counts[mode] += 1
    return counts


if __name__ == '__main__':
    counts = check(Path(__file__).resolve().parents[1])
    print('PASS: Markdown declaration structure and preserved bytes', counts,
          '; meaning and permissions require human/Agent review')
