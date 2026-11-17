"""Build the local demo or train on a supplied corrected ASSISTments CSV."""
import argparse
import csv
import hashlib
import json
import sqlite3
import sys
import statistics
import time
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.data.dataset import synthetic_events,load_assistments,describe
from src.ml.model import features,group_split,train_logistic,predict,history_predict,metrics,save
from src.retrieval.materials import MATERIALS,REAL_MATERIALS

def build(source=None,max_students=None,synthetic=False):
    default_real=ROOT/'data/raw/skill_builder_data_corrected_collapsed.csv'
    if source is None and default_real.exists() and not synthetic:source=default_real
    if source:
        source=Path(source)
        sidecar=Path(str(source)+':Zone.Identifier')
        official_id='1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE'
        verified=source.name=='skill_builder_data_corrected_collapsed.csv' and sidecar.exists() and official_id in sidecar.read_text(errors='replace')
        kind='ASSISTments 2009–2010 Skill Builder corrected collapsed — download URL matched' if verified else 'USER-SUPPLIED ASSISTments-like CSV — correction unverified'
        rows,rejected=load_assistments(source)
        source_file=str(source);source_file_bytes=source.stat().st_size
        with source.open('rb') as f:source_sha256=hashlib.file_digest(f,'sha256').hexdigest()
        source_valid_rows=len(rows)
        if max_students:
            ids=set(sorted({r['user_id'] for r in rows})[:max_students])
            rows=[r for r in rows if r['user_id'] in ids]
        materials=REAL_MATERIALS
    else:
        rows=synthetic_events();rejected={};kind='SYNTHETIC DEMONSTRATION — NOT ASSISTments';source_valid_rows=len(rows)
        source_file=None;source_file_bytes=None;source_sha256=None;verified=False;materials=MATERIALS
    if len(rows)<100:raise ValueError('At least 100 valid responses required')
    counts=Counter(r['user_id'] for r in rows)
    skill_counts=Counter(r['skill_name'] for r in rows)
    skill_id_counts=Counter(r['skill_id'] for r in rows)
    eda={'dataset':kind,'source_file':source_file,'source_file_bytes':source_file_bytes,
         'source_sha256':source_sha256,
         'source_rows':source_valid_rows+sum(rejected.values()),'source_url_matched':verified,
         'source_valid_rows':source_valid_rows,'selected_rows':len(rows),
         'selected_fraction_of_valid_rows':len(rows)/source_valid_rows,
         'students':len(counts),'skills':len(skill_id_counts),'skill_name_values':len(skill_counts),
         'target_counts':dict(Counter(str(r['correct']) for r in rows)),
         'responses_per_student':{'min':min(counts.values()),'median':statistics.median(counts.values()),'max':max(counts.values())},
         'skill_counts':dict(sorted(skill_counts.items())), 'rejected':rejected,
         'nulls_after_cleaning':0}
    (ROOT/'reports/eda.json').write_text(json.dumps(eda,ensure_ascii=False,indent=2))
    (ROOT/'data/demo').mkdir(parents=True,exist_ok=True)
    path=ROOT/'data/demo/interactions.csv'
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['user_id','skill_id','skill_name','order_id','correct']);writer.writeheader()
        writer.writerows({k:r[k] for k in writer.fieldnames} for r in rows)
    prepared=features(rows);train,test=group_split(prepared)
    train_users={r['user_id'] for r in train};test_users={r['user_id'] for r in test}
    if train_users & test_users:raise AssertionError('User leakage across train/test')
    baseline=sum(r['correct'] for r in train)/len(train)
    started=time.perf_counter();model=train_logistic(train);training_seconds=time.perf_counter()-started
    scores={
      'constant':metrics(test,[baseline]*len(test)),
      'history_rule':metrics(test,[history_predict(r,baseline) for r in test]),
      'logistic_sgd':metrics(test,[predict(model,r) for r in test]),
    }
    save(model,ROOT/'models/model.json')
    with (ROOT/'reports/model_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['model']+list(scores['constant']));w.writeheader()
        for name,score in scores.items():w.writerow({'model':name,**score})
    info={'dataset':kind,'source_file':source_file,'source_file_bytes':source_file_bytes,
          'source_sha256':source_sha256,
          'source_url_matched':verified,'source_rows':source_valid_rows+sum(rejected.values()),
          'dataset_summary':describe(rows),'source_valid_rows':source_valid_rows,
          'selected_fraction_of_valid_rows':len(rows)/source_valid_rows,'rejected':rejected,
          'train_responses':len(train),'test_responses':len(test),
          'train_students':len(train_users),
          'test_students':len(test_users),'split_user_overlap':0,
          'split_seed':42,'validation_scheme':'disjoint user_id groups; online causal history within each test user',
          'prediction_target':'correct for the next response on a specified skill',
          'features':model['features'],'forbidden_current_fields_used':[],
          'model':'logistic_sgd','model_epochs':model['epochs'],
          'model_training_seconds':round(training_seconds,3),'metrics':scores,
          'limitation':'Synthetic data cannot establish real-world predictive validity.' if not source else 'Offline user holdout is not prospective validation; predicted next response is not mastery.'}
    (ROOT/'reports/experiment.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    db=sqlite3.connect(ROOT/'data/demo/edupath.db')
    db.executescript('''DROP TABLE IF EXISTS interactions;DROP TABLE IF EXISTS students;
      DROP TABLE IF EXISTS skills;DROP TABLE IF EXISTS materials;DROP TABLE IF EXISTS prerequisites;
      CREATE TABLE students(user_id TEXT PRIMARY KEY);
      CREATE TABLE skills(skill_id TEXT PRIMARY KEY,skill_name TEXT NOT NULL);
      CREATE TABLE interactions(id INTEGER PRIMARY KEY,user_id TEXT,skill_id TEXT,order_id REAL,correct INTEGER,
        FOREIGN KEY(user_id) REFERENCES students(user_id),FOREIGN KEY(skill_id) REFERENCES skills(skill_id));
      CREATE TABLE materials(skill_id TEXT PRIMARY KEY,title TEXT,explanation TEXT,example TEXT,source TEXT,url TEXT);
      CREATE TABLE prerequisites(parent TEXT,child TEXT,PRIMARY KEY(parent,child));''')
    db.execute('CREATE INDEX interactions_user_order ON interactions(user_id,order_id,id)')
    db.executemany('INSERT INTO students VALUES (?)',[(x,) for x in sorted({r['user_id'] for r in rows})])
    db.executemany('INSERT INTO skills VALUES (?,?)',sorted({(r['skill_id'],r['skill_name']) for r in rows}))
    db.executemany('INSERT INTO interactions(user_id,skill_id,order_id,correct) VALUES (?,?,?,?)',
                   [(r['user_id'],r['skill_id'],r['order_id'],r['correct']) for r in rows])
    db.executemany('INSERT INTO materials VALUES (:skill_id,:title,:explanation,:example,:source,:url)',materials)
    from src.recommendation.trajectory import EDGES,REAL_EDGES
    skillset={r['skill_id'] for r in rows}
    edges=REAL_EDGES if source else EDGES
    db.executemany('INSERT INTO prerequisites VALUES (?,?)',[(a,b) for a,b in edges if a in skillset and b in skillset])
    db.commit();db.close()
    # MLflow is optional at build time; the reproducible JSON/CSV are always produced.
    try:
        import mlflow
        mlflow.set_tracking_uri((ROOT/'mlruns').as_uri());mlflow.set_experiment('EduPath ML')
        for name,score in scores.items():
            with mlflow.start_run(run_name=name):
                mlflow.log_params({'dataset':kind,'split_seed':42,'train_students':info['train_students']})
                mlflow.log_metrics({k:v for k,v in score.items() if v is not None})
                mlflow.log_artifact(str(ROOT/'reports/model_metrics.csv'))
        info['mlflow']='logged';(ROOT/'reports/experiment.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    except ImportError: info['mlflow']='unavailable: package not installed';(ROOT/'reports/experiment.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
    print(json.dumps(info,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--assistments-csv',type=Path)
    p.add_argument('--max-students',type=int,default=None,help='Optional deterministic resource cap; default uses all valid rows')
    p.add_argument('--synthetic',action='store_true',help='Explicitly use synthetic demo data')
    args=p.parse_args()
    build(args.assistments_csv,args.max_students,args.synthetic)
