"""Recreate only SQLite from the official local CSV; never train or overwrite artifacts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.dataset import load_assistments, describe
from src.retrieval.materials import REAL_MATERIALS
from src.recommendation.trajectory import REAL_EDGES

SCHEMA = '''
CREATE TABLE students(user_id TEXT PRIMARY KEY);
CREATE TABLE skills(skill_id TEXT PRIMARY KEY,skill_name TEXT NOT NULL);
CREATE TABLE interactions(id INTEGER PRIMARY KEY,user_id TEXT,skill_id TEXT,order_id REAL,correct INTEGER,
  FOREIGN KEY(user_id) REFERENCES students(user_id),FOREIGN KEY(skill_id) REFERENCES skills(skill_id));
CREATE TABLE materials(skill_id TEXT PRIMARY KEY,title TEXT,explanation TEXT,example TEXT,source TEXT,url TEXT);
CREATE TABLE prerequisites(parent TEXT,child TEXT,PRIMARY KEY(parent,child));
CREATE INDEX interactions_user_order ON interactions(user_id,order_id,id);
'''


def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(f'База уже существует: {destination}. Она не будет перезаписана.')
    expected = json.loads((ROOT / 'reports/experiment.json').read_text())
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != expected['source_sha256']:
        raise ValueError('CSV отличается от файла сохранённого эксперимента. Проверьте исправленную collapsed-версию и SHA-256.')
    rows, rejected = load_assistments(source)
    summary = describe(rows)
    if {k: summary[k] for k in ('responses', 'students', 'skills')} != {
            k: expected['dataset_summary'][k] for k in ('responses', 'students', 'skills')}:
        raise ValueError('Количество событий/учеников/навыков не совпадает с экспериментом.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.edupath-', suffix='.db.tmp', dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        with sqlite3.connect(temporary) as db:
            db.executescript(SCHEMA)
            db.executemany('INSERT INTO students VALUES (?)', [(x,) for x in sorted({r['user_id'] for r in rows})])
            db.executemany('INSERT INTO skills VALUES (?,?)', sorted({(r['skill_id'], r['skill_name']) for r in rows}))
            db.executemany('INSERT INTO interactions(user_id,skill_id,order_id,correct) VALUES (?,?,?,?)',
                           ((r['user_id'], r['skill_id'], r['order_id'], r['correct']) for r in rows))
            db.executemany('INSERT INTO materials VALUES (:skill_id,:title,:explanation,:example,:source,:url)', REAL_MATERIALS)
            db.executemany('INSERT INTO prerequisites VALUES (?,?)', REAL_EDGES)
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        # Atomic creation without replacing a database created by another process.
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {'database': str(destination), **summary, 'rejected': rejected,
            'materials': len(REAL_MATERIALS), 'edges': len(REAL_EDGES), 'training': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/raw/skill_builder_data_corrected_collapsed.csv')
    parser.add_argument('--destination', type=Path, default=ROOT / 'data/demo/edupath.db')
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination), ensure_ascii=False, indent=2))
