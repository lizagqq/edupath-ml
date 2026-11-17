"""Audit skill mapping and recommendation coverage without retraining."""
import json
import sqlite3
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.api.service import Service
from src.ml.model import load
from src.recommendation.trajectory import topological,REAL_EDGES
from src.retrieval.materials import REAL_MATERIALS,REAL_SOURCE_NAMES

def main():
    db=sqlite3.connect(ROOT/'data/demo/edupath.db');db.row_factory=sqlite3.Row
    skills=db.execute('SELECT COUNT(*) FROM skills').fetchone()[0]
    interactions=db.execute('SELECT COUNT(*) FROM interactions').fetchone()[0]
    students=db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    materials=[dict(r) for r in db.execute('''SELECT m.skill_id,s.skill_name,m.title,
      (SELECT COUNT(*) FROM interactions i WHERE i.skill_id=m.skill_id) AS responses
      FROM materials m JOIN skills s ON s.skill_id=m.skill_id ORDER BY m.skill_id''')]
    edges=[tuple(r) for r in db.execute('SELECT parent,child FROM prerequisites ORDER BY parent,child')]
    assert skills==149 and interactions==283105 and students==4163
    assert len(materials)==len(REAL_MATERIALS) and len(edges)==len(REAL_EDGES)
    assert set(edges)==set(REAL_EDGES) and all(m['responses']>0 for m in materials)
    assert all(next(m['skill_name'] for m in materials if m['skill_id']==sid)==name
               for sid,name in REAL_SOURCE_NAMES.items())
    covered=sum(m['responses'] for m in materials)
    students_covered=db.execute('SELECT COUNT(DISTINCT user_id) FROM interactions WHERE skill_id IN (SELECT skill_id FROM materials)').fetchone()[0]
    topological([m['skill_id'] for m in materials],edges)
    absent=db.execute('''SELECT s.user_id FROM students s WHERE NOT EXISTS
      (SELECT 1 FROM interactions i WHERE i.user_id=s.user_id AND i.skill_id IN (SELECT skill_id FROM materials)) LIMIT 1''').fetchone()[0]
    db.close()
    service=Service();empty=service.trajectory(absent)
    assert not empty['trajectory'] and not empty['focus_skill_ids']
    model=load(service.model_path);forbidden={'correct','attempt_count','hint_count'}
    assert not (forbidden & set(model['features']))
    report={'dataset':service.info()['dataset'],'total_skill_ids':skills,'material_skill_ids':len(materials),
            'unsupported_skill_ids':skills-len(materials),'prerequisite_edges':edges,
            'mapping':materials,'total_responses':interactions,'supported_responses':covered,
            'supported_response_fraction':covered/interactions,'total_students':students,
            'students_with_supported_skill':students_covered,
            'student_without_supported_skill':absent,'empty_route_guard_verified':True,
            'model_features':model['features'],'forbidden_current_fields_used':[]}
    out=ROOT/'reports/integration_audit.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:report[k] for k in ['total_skill_ids','material_skill_ids','unsupported_skill_ids','supported_responses','supported_response_fraction','students_with_supported_skill','student_without_supported_skill','empty_route_guard_verified']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
