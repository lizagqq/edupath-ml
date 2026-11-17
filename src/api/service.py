"""Application services shared by FastAPI and the dependency-free smoke server."""
import json
import sqlite3
from pathlib import Path
from src.api.contracts import APP_VERSION, TRAJECTORY_CONTRACT_VERSION, validate_trajectory
from src.ml.model import load,predict
from src.recommendation.trajectory import personalized_plan
from src.retrieval.materials import search,add_practice

ROOT=Path(__file__).resolve().parents[2]

class Service:
    def __init__(self,root=ROOT):
        self.root=Path(root)
        self.db_path=self.root/'data/demo/edupath.db'
        self.model_path=self.root/'models/model.json'
        self.report_path=self.root/'reports/experiment.json'
    def ready(self):return self.db_path.exists() and self.model_path.exists() and self.report_path.exists()
    def _db(self):
        db=sqlite3.connect(self.db_path);db.row_factory=sqlite3.Row;return db
    def health(self):return {'app_version':APP_VERSION,'trajectory_contract_version':TRAJECTORY_CONTRACT_VERSION,'status':'ok' if self.ready() else 'not_ready','dataset':self.info().get('dataset','unknown') if self.ready() else None}
    def info(self):return json.loads(self.report_path.read_text()) if self.report_path.exists() else {}
    def students(self,limit=20):
        with self._db() as db:
            return [r['user_id'] for r in db.execute('''SELECT user_id FROM interactions
                GROUP BY user_id ORDER BY COUNT(*) DESC,user_id LIMIT ?''',(limit,))]
    def skills(self):
        with self._db() as db:return [dict(r) for r in db.execute('SELECT * FROM skills ORDER BY skill_name')]
    def materials(self,skill=None,query='',limit=3):
        with self._db() as db:docs=[dict(r) for r in db.execute('SELECT * FROM materials')]
        return add_practice(search(query,skill,limit,docs))
    def profile(self,user_id):
        with self._db() as db:
            if not db.execute('SELECT 1 FROM students WHERE user_id=?',(user_id,)).fetchone():raise KeyError(user_id)
            events=[dict(r) for r in db.execute('SELECT * FROM interactions WHERE user_id=? ORDER BY order_id,id',(user_id,))]
            allskills=[dict(r) for r in db.execute('SELECT * FROM skills')]
            display={r['skill_id']:r['title'] for r in db.execute('SELECT skill_id,title FROM materials')}
        total=len(events);correct=sum(r['correct'] for r in events)
        model=load(self.model_path);out=[]
        for s in allskills:
            subset=[r for r in events if r['skill_id']==s['skill_id']];n=len(subset);c=sum(r['correct'] for r in subset)
            feat={'skill_id':s['skill_id'],'prior_count':total,'prior_success':(correct+1)/(total+2),
                  'prior_skill_count':n,'prior_skill_success':(c+1)/(n+2)}
            out.append({'skill_id':s['skill_id'],'skill_name':s['skill_name'],
                        'display_name':display.get(s['skill_id'],s['skill_name']),'observations':n,
                        'observed_accuracy':c/n if n else None,
                        'predicted_probability':round(predict(model,feat),4),
                        'confidence':'недостаточно данных' if n<3 else ('ограниченная' if n<10 else 'больше наблюдений')})
        return {'user_id':user_id,'responses':total,'observed_accuracy':correct/total if total else None,
                'skills':sorted(out,key=lambda x:x['skill_name'])}
    def trajectory(self,user_id):
        profile=self.profile(user_id)
        with self._db() as db:
            docs=add_practice([dict(r) for r in db.execute('SELECT * FROM materials')])
            edges=[tuple(r) for r in db.execute('SELECT parent,child FROM prerequisites')]
        candidates=[{**x,'dataset_skill_name':x['skill_name']} for x in profile['skills']]
        profile.update(personalized_plan(candidates,docs,edges))
        profile['contract_version'] = TRAJECTORY_CONTRACT_VERSION
        return validate_trajectory(profile)
