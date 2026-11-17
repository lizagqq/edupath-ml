"""Record existing ASSISTments experiment in local MLflow without retraining."""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main(force=False):
    import mlflow
    result_file=ROOT/'reports/mlflow_runs.json'
    if result_file.exists() and not force:
        print('Existing record:',result_file,'(use --force to create another set of runs)');return
    info=json.loads((ROOT/'reports/experiment.json').read_text())
    if not info['dataset'].startswith('ASSISTments'):
        raise RuntimeError('The current experiment is not the real ASSISTments run')
    mlflow.set_tracking_uri((ROOT/'mlruns').as_uri())
    mlflow.set_experiment('EduPath ML — ASSISTments 2009–2010')
    runs={}
    for name,score in info['metrics'].items():
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params({'dataset_sha256':info['source_sha256'],
                               'train_students':info['train_students'],'test_students':info['test_students'],
                               'train_responses':info['train_responses'],'test_responses':info['test_responses'],
                               'split_seed':info['split_seed'],'method':name})
            mlflow.log_metrics({k:v for k,v in score.items() if v is not None})
            mlflow.log_artifact(str(ROOT/'reports/model_metrics.csv'))
            mlflow.log_artifact(str(ROOT/'reports/experiment.json'))
            if name=='logistic_sgd':mlflow.log_artifact(str(ROOT/'models/model.json'))
            runs[name]=run.info.run_id
    result_file.write_text(json.dumps({'tracking_uri':(ROOT/'mlruns').as_uri(),'runs':runs},indent=2))
    print(json.dumps(runs,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--force',action='store_true')
    main(p.parse_args().force)
