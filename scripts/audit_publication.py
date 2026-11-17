"""Scan publishable files and all reachable Git blobs; never print matched secrets."""
import argparse
import json
from pathlib import Path
import re
import subprocess

PATTERNS = {
    'github_token': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'aws_access_key': re.compile(rb'(?:AKIA|ASIA)[A-Z0-9]{16}'),
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'credential_url': re.compile(rb'https?://[^\s/@:]+:[^\s/@]+@'),
    'slack_token': re.compile(rb'xox[baprs]-[A-Za-z0-9-]{20,}'),
    'literal_secret': re.compile(rb'''(?i)(?:password|api[_-]?key|access[_-]?token|secret[_-]?key)\s*[=:]\s*["'][A-Za-z0-9/+_=-]{12,}["']'''),
}


def forbidden_path(path):
    p = Path(path)
    return (any(x in {'.venv', '__pycache__', '.aws', '.ssh', '.codex', '.agents', '.git'} for x in p.parts)
            or p.name.startswith('.env') and p.name != '.env.example'
            or p.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.p12', '.pfx', '.docx', '.pdf', '.zip'}
            or path.startswith(('data/raw/', 'data/demo/')) and p.name != '.gitkeep'
            or path == 'docs/figures/document_evidence.json'
            or p.name in {'secrets.toml', '.git-credentials', '.netrc'}
            or ':Zone.Identifier' in p.name)


def inspect_blob(data):
    return [name for name, pattern in PATTERNS.items() if pattern.search(data)]


def audit_files(root, paths):
    root = Path(root)
    findings, size = [], 0
    for path in paths:
        p = root / path
        if p.is_symlink():
            findings.append({'path': path, 'reason': 'symlink'}); continue
        if forbidden_path(path): findings.append({'path': path, 'reason': 'excluded category'})
        data = p.read_bytes(); size += len(data)
        if len(data) > 50 * 1024 * 1024: findings.append({'path': path, 'reason': 'over 50 MiB'})
        for kind in inspect_blob(data): findings.append({'path': path, 'reason': kind})
    return {'files': len(paths), 'bytes': size, 'findings': findings}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def audit_repository(root):
    paths = [p for p in git(root, 'ls-files', '-z').decode().split('\0') if p]
    result = audit_files(root, paths)
    history_findings = []
    blobs = 0
    for item in git(root, 'rev-list', '--objects', '--all').decode().splitlines():
        oid, _, path = item.partition(' ')
        if git(root, 'cat-file', '-t', oid).strip() != b'blob': continue
        blobs += 1
        if path and forbidden_path(path): history_findings.append({'object': oid, 'path': path, 'reason': 'excluded category'})
        for kind in inspect_blob(git(root, 'cat-file', 'blob', oid)):
            history_findings.append({'object': oid, 'path': path, 'reason': kind})
    return {**result, 'history_blobs_scanned': blobs, 'history_findings': history_findings}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    args = parser.parse_args()
    result = audit_repository(args.repository)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result['findings'] or result['history_findings']))
