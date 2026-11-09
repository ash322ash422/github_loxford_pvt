import hashlib
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def safe_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or Path(relative).is_absolute():
        raise ValueError('Path escapes allowed root')
    return path


def scan_directory(root):
    root = Path(root).resolve()
    result = []
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            continue
        if p.is_file():
            relative = p.relative_to(root).as_posix()
            safe_path(root, relative)
            result.append(dict(path=relative, type=p.suffix.lower(), size=p.stat().st_size,
                               sha256=digest(p)))
    return result
