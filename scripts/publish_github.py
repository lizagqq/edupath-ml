"""Publish the prepared snapshot after browser login. No force, remote deletion or history rewrite."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_publication import audit_repository


def run(args, cwd=None, check=True):
    return subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def publish(snapshot):
    snapshot = Path(snapshot).resolve()
    if not shutil.which('gh'):
        raise RuntimeError('GitHub CLI не установлен. Установите gh и выполните gh auth login --web. Токен в чат не нужен.')
    if run(['gh', 'auth', 'status', '--hostname', 'github.com'], check=False).returncode:
        raise RuntimeError('Нужна авторизация: gh auth login --hostname github.com --git-protocol https --web')
    user = json.loads(run(['gh', 'api', 'user']).stdout)
    if user['login'].lower() != 'lizagqq': raise RuntimeError('Авторизован другой аккаунт; ожидается lizagqq.')
    if not snapshot.is_dir(): raise FileNotFoundError('Сначала выполните prepare_github_release.py.')
    audit = audit_repository(snapshot)
    if audit['findings'] or audit['history_findings']: raise ValueError('Снимок не прошёл проверку файлов/истории.')
    if run(['git', 'status', '--porcelain'], cwd=snapshot).stdout.strip():
        raise RuntimeError('Снимок изменён после коммита; подготовьте новую проверенную копию.')
    name = 'lizagqq/edupath-ml'
    probe = run(['gh', 'api', f'repos/{name}'], check=False)
    if probe.returncode:
        if '404' not in probe.stderr:
            raise RuntimeError('GitHub не дал проверить репозиторий. Создание при сетевой ошибке не выполняется.')
        run(['gh', 'repo', 'create', name, '--private', '--description', 'EduPath ML: анализ ответов и индивидуальный план повторения'])
        info = json.loads(run(['gh', 'api', f'repos/{name}']).stdout)
    else:
        info = json.loads(probe.stdout)
    if not info['private']: raise RuntimeError('Существующий репозиторий не приватный; его настройки не изменены.')
    run(['gh', 'auth', 'setup-git', '--hostname', 'github.com'])
    staging = ROOT / '_publication' / ('github-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    staging.parent.mkdir(parents=True, exist_ok=True)
    run(['git', 'clone', f'https://github.com/{name}.git', str(staging)])
    has_head = run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=staging, check=False).returncode == 0
    if has_head:
        old_audit = audit_repository(staging)
        if old_audit['findings'] or old_audit['history_findings']:
            raise RuntimeError('Существующая история не прошла проверку; она сохранена, публикация остановлена.')
        branch = 'edupath-publication-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S%f')
        run(['git', 'switch', '-c', branch], cwd=staging)
    else:
        branch = 'main'
        run(['git', 'checkout', '-b', branch], cwd=staging)
    paths = run(['git', 'ls-files', '-z'], cwd=snapshot).stdout.split('\0')
    for relative in filter(None, paths):
        target = staging / relative
        # Never follow an existing repository symlink outside this staging tree.
        chain = [target, *target.parents]
        if any(p.is_symlink() for p in chain): raise RuntimeError(f'Символическая ссылка в пути: {relative}')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot / relative, target)
    run(['git', 'add', '--all'], cwd=staging)
    check = audit_repository(staging)
    if check['findings'] or check['history_findings']: raise RuntimeError('Проверка перед коммитом не пройдена.')
    if run(['git', 'diff', '--cached', '--quiet'], cwd=staging, check=False).returncode:
        email = f"{user['id']}+{user['login']}@users.noreply.github.com"
        run(['git', '-c', f"user.name={user['login']}", '-c', f'user.email={email}', 'commit', '-m',
             'Publish current EduPath ML 0.2.0 with safe setup documentation'], cwd=staging)
    check = audit_repository(staging)
    if check['findings'] or check['history_findings']: raise RuntimeError('История нового коммита не прошла проверку.')
    run(['git', 'push', 'origin', f'HEAD:refs/heads/{branch}'], cwd=staging)
    commit = run(['git', 'rev-parse', 'HEAD'], cwd=staging).stdout.strip()
    remote = run(['git', 'ls-remote', 'origin', f'refs/heads/{branch}'], cwd=staging).stdout.split()[0]
    info = json.loads(run(['gh', 'api', f'repos/{name}']).stdout)
    assert remote == commit and info['private']
    result = {'url': info['html_url'], 'branch': branch, 'commit': commit, 'remote_commit_verified': True,
              'private_verified': True, 'existing_default_branch_preserved': has_head}
    (ROOT / '_publication/github_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT / '_publication/edupath-ml')
    args = parser.parse_args()
    try:
        print(json.dumps(publish(args.snapshot), ensure_ascii=False, indent=2))
    except (RuntimeError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        # Do not dump process environments or authentication material.
        print(f'Публикация не завершена: {exc if not isinstance(exc, subprocess.CalledProcessError) else "команда Git/GitHub завершилась ошибкой"}', file=sys.stderr)
        raise SystemExit(1)
