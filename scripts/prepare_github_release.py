"""Export a reviewed Git snapshot without touching the working project's .git or data."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_publication import audit_files, audit_repository


def prepare(destination):
    destination = Path(destination).resolve()
    if destination.exists(): raise FileExistsError(f'Не перезаписываю существующий каталог: {destination}')
    # Explicit, separate metadata is needed when the workspace's .git is read-only.
    with tempfile.TemporaryDirectory(prefix='edupath-ignore-') as metadata:
        subprocess.run(['git', 'init', '--bare', '--quiet', metadata], check=True)
        names = subprocess.check_output(['git', '--git-dir', metadata, '--work-tree', str(ROOT),
                                         'ls-files', '--others', '--exclude-standard', '-z']).decode()
    paths = sorted(p for p in names.split('\0') if p)
    report = audit_files(ROOT, paths)
    if report['findings']: raise ValueError(json.dumps(report, ensure_ascii=False))
    destination.mkdir(parents=True)
    for relative in paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    subprocess.run(['git', 'init', '-b', 'main', '--quiet', str(destination)], check=True)
    subprocess.run(['git', '-C', str(destination), 'add', '--all'], check=True)
    # A local snapshot, not an assertion of the owner's verified GitHub email.
    subprocess.run(['git', '-C', str(destination), '-c', 'user.name=EduPath snapshot',
                    '-c', 'user.email=snapshot@localhost', 'commit', '--quiet',
                    '-m', 'Prepare EduPath ML 0.2.0 for private publication'], check=True)
    committed = audit_repository(destination)
    if committed['findings'] or committed['history_findings']: raise ValueError(json.dumps(committed))
    commit = subprocess.check_output(['git', '-C', str(destination), 'rev-parse', 'HEAD']).decode().strip()
    archive = destination.parent / 'edupath-ml-source.zip'
    if archive.exists(): raise FileExistsError(f'Не перезаписываю архив: {archive}')
    with ZipFile(archive, 'x', ZIP_DEFLATED) as z:
        for path in paths: z.write(destination / path, 'edupath-ml/' + path)
    result = {**committed, 'snapshot': str(destination), 'commit': commit, 'archive': str(archive),
              'remote_created': False, 'pushed': False, 'existing_working_files_removed': False}
    (destination.parent / 'publication_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT / '_publication/edupath-ml')
    args = parser.parse_args()
    print(json.dumps(prepare(args.destination), ensure_ascii=False, indent=2))
