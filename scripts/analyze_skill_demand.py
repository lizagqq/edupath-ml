"""Rank real ASSISTments skill gaps using existing model and stored histories."""

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.api.service import Service
from src.ml.model import load, predict


def analyze(service=None):
    service = service or Service()
    model = load(service.model_path)
    with sqlite3.connect(service.db_path) as db:
        totals = {uid: (n, correct) for uid, n, correct in db.execute(
            "SELECT user_id, COUNT(*), SUM(correct) FROM interactions GROUP BY user_id"
        )}
        names = dict(db.execute("SELECT skill_id, skill_name FROM skills"))
        rows = db.execute("""SELECT user_id, skill_id, COUNT(*), SUM(correct)
            FROM interactions GROUP BY user_id, skill_id""").fetchall()
    demand = defaultdict(lambda: {"students_with_3_answers": 0,
                                  "students_with_weak_forecast": 0,
                                  "observed_answers": 0})
    examples = defaultdict(list)
    for uid, sid, n, correct in rows:
        if n < 3:
            continue
        total_n, total_correct = totals[uid]
        probability = predict(model, {
            "skill_id": sid, "prior_count": total_n,
            "prior_success": (total_correct + 1) / (total_n + 2),
            "prior_skill_count": n, "prior_skill_success": (correct + 1) / (n + 2),
        })
        item = demand[sid]
        item["students_with_3_answers"] += 1
        item["observed_answers"] += n
        item["students_with_weak_forecast"] += probability < 0.5
        if uid in {"79021", "75169", "78970"}:
            examples[uid].append({"skill_id": sid, "skill_name": names[sid],
                                  "observations": n, "predicted_probability": round(probability, 4)})
    ordered = [dict(skill_id=sid, skill_name=names[sid], **values)
               for sid, values in demand.items()]
    ordered.sort(key=lambda x: (-x["students_with_weak_forecast"],
                                -x["observed_answers"], x["skill_id"]))
    return {
        "dataset": service.info()["dataset"],
        "method": "Post-history next-answer forecast; at least 3 answers per student and skill; weak when p(correct)<0.5. This is resource planning, not learning-effect evaluation.",
        "skills": ordered,
        "examples": {uid: sorted(items, key=lambda x: x["predicted_probability"])[:15]
                     for uid, items in examples.items()},
    }


if __name__ == "__main__":
    result = analyze()
    target = ROOT / "reports/skill_demand.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({"report": str(target), "top_weak_skills": result["skills"][:15]},
                     ensure_ascii=False, indent=2))
