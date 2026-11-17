"""Update only materials and documented prerequisite edges in existing SQLite."""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.api.service import Service
from src.recommendation.trajectory import REAL_EDGES, topological
from src.retrieval.materials import REAL_MATERIALS, REAL_SOURCE_NAMES


def sha(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def sync(service=None):
    service = service or Service()
    if not service.info().get("dataset", "").startswith("ASSISTments"):
        raise ValueError("Knowledge base update requires the real ASSISTments artifacts")
    ids = [item["skill_id"] for item in REAL_MATERIALS]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate material skill ID")
    topological(ids, REAL_EDGES)
    model_hash = sha(service.model_path)
    metrics_hash = sha(service.report_path)
    with sqlite3.connect(service.db_path) as db:
        names = dict(db.execute("SELECT skill_id, skill_name FROM skills"))
        missing = set(ids) - names.keys()
        if missing:
            raise ValueError(f"Material IDs absent from dataset: {sorted(missing)}")
        mismatches = {sid: (expected, names[sid]) for sid, expected in REAL_SOURCE_NAMES.items()
                      if names.get(sid) != expected}
        if mismatches:
            raise ValueError(f"Source skill names differ: {mismatches}")
        old_count = db.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
        for item in REAL_MATERIALS:
            db.execute("""INSERT INTO materials(skill_id,title,explanation,example,source,url)
                VALUES (:skill_id,:title,:explanation,:example,:source,:url)
                ON CONFLICT(skill_id) DO UPDATE SET title=excluded.title,
                explanation=excluded.explanation,example=excluded.example,
                source=excluded.source,url=excluded.url""", item)
        for parent, child in REAL_EDGES:
            db.execute("INSERT OR IGNORE INTO prerequisites(parent,child) VALUES (?,?)", (parent, child))
        total = db.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
        edges = db.execute("SELECT parent,child FROM prerequisites ORDER BY parent,child").fetchall()
        if total != len(REAL_MATERIALS) or len(edges) != len(REAL_EDGES):
            raise ValueError("Unexpected knowledge-base rows; transaction rolled back")
    if sha(service.model_path) != model_hash or sha(service.report_path) != metrics_hash:
        raise AssertionError("Model or experiment artifact changed")
    return {"dataset": service.info()["dataset"], "materials_before": old_count,
            "materials_after": total, "prerequisite_edges": edges,
            "model_sha256": model_hash, "experiment_sha256": metrics_hash,
            "note": "No model training or metric changes"}


if __name__ == "__main__":
    result = sync()
    target = ROOT / "reports/knowledge_base_sync.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
