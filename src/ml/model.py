"""Causal features, group holdout, dependency-free logistic model and metrics."""
import json
import math
import random
from collections import defaultdict
from pathlib import Path

def features(rows):
    ordered=sorted(rows,key=lambda r:(str(r['user_id']),float(r['order_id']),r.get('_source_row',0)))
    total=defaultdict(lambda:[0,0]);skill=defaultdict(lambda:[0,0]);out=[]
    for r in ordered:
        u=str(r['user_id']);s=str(r['skill_id']);n,c=total[u];sn,sc=skill[u,s]
        item=dict(r,prior_count=n,prior_success=(c+1)/(n+2),
                  prior_skill_count=sn,prior_skill_success=(sc+1)/(sn+2))
        out.append(item)
        total[u][0]+=1;total[u][1]+=int(r['correct'])
        skill[u,s][0]+=1;skill[u,s][1]+=int(r['correct'])
    return out

def group_split(rows,seed=42,test_fraction=.2):
    users=sorted({str(r['user_id']) for r in rows});random.Random(seed).shuffle(users)
    test=set(users[:max(1,round(len(users)*test_fraction))])
    return [r for r in rows if str(r['user_id']) not in test],[r for r in rows if str(r['user_id']) in test]

def vector(r,skills):
    a=[1.,math.log1p(r['prior_count'])/4,r['prior_success'],
       math.log1p(r['prior_skill_count'])/3,r['prior_skill_success']]
    return a+[float(r['skill_id']==s) for s in skills]

def sigmoid(x):
    x=max(-30,min(30,x));return 1/(1+math.exp(-x))

def train_logistic(train,epochs=18,rate=.12,seed=42):
    skills=sorted({r['skill_id'] for r in train});dim=5+len(skills)
    skill_index={s:5+i for i,s in enumerate(skills)}
    weights=[0.]*dim; rng=random.Random(seed)
    # Cache only five numeric terms and the active category. Dense one-hot
    # updates would multiply work by the 149 skills in the real file.
    data=[]
    for r in train:
        x=(1.,math.log1p(r['prior_count'])/4,r['prior_success'],
           math.log1p(r['prior_skill_count'])/3,r['prior_skill_success'])
        data.append((x,skill_index[r['skill_id']],r['correct']))
    for epoch in range(epochs):
        rng.shuffle(data)
        for x,category,target in data:
            err=sigmoid(sum(weights[i]*x[i] for i in range(5))+weights[category])-target
            for i in range(5): weights[i]-=rate*(err*x[i]+.00002*weights[i])
            weights[category]-=rate*(err+.00002*weights[category])
        rate*=.88
    return {'type':'logistic_sgd','weights':weights,'skills':skills,'skill_index':skill_index,
            'features':['bias','log_prior_count','prior_success','log_prior_skill_count','prior_skill_success','skill_one_hot'],
            'seed':seed,'epochs':epochs}

def predict(model,r):
    w=model['weights'];s=r['skill_id']
    idx=model.get('skill_index',{}).get(s)
    if idx is None:
        try:idx=5+model['skills'].index(s)
        except ValueError:idx=None
    x=(1.,math.log1p(r['prior_count'])/4,r['prior_success'],
       math.log1p(r['prior_skill_count'])/3,r['prior_skill_success'])
    return sigmoid(sum(w[i]*x[i] for i in range(5))+(w[idx] if idx is not None else 0.))

def auc(y,p):
    pairs=sorted(zip(p,y));neg=sum(1-v for v in y);pos=sum(y)
    if not neg or not pos:return None
    posrank=0;i=0
    while i<len(pairs):
        j=i+1
        while j<len(pairs) and pairs[j][0]==pairs[i][0]:j+=1
        average_rank=(i+1+j)/2
        posrank+=average_rank*sum(v for _,v in pairs[i:j])
        i=j
    return (posrank-pos*(pos+1)/2)/(pos*neg)

def metrics(rows,probs):
    y=[r['correct'] for r in rows];n=len(y);pred=[int(p>=.5) for p in probs]
    tp=sum(a==1 and b==1 for a,b in zip(y,pred));tn=sum(a==0 and b==0 for a,b in zip(y,pred))
    fp=sum(a==0 and b==1 for a,b in zip(y,pred));fn=sum(a==1 and b==0 for a,b in zip(y,pred))
    pr=tp/(tp+fp) if tp+fp else 0;rec=tp/(tp+fn) if tp+fn else 0
    return {'accuracy':(tp+tn)/n,'precision':pr,'recall':rec,'f1':2*pr*rec/(pr+rec) if pr+rec else 0,
            'roc_auc':auc(y,probs),'log_loss':-sum(v*math.log(max(1e-15,min(1-1e-15,p)))+(1-v)*math.log(max(1e-15,min(1-1e-15,1-p))) for v,p in zip(y,probs))/n,
            'brier':sum((v-p)**2 for v,p in zip(y,probs))/n}

def history_predict(r,global_rate):
    return (r['prior_skill_success']*r['prior_skill_count']+global_rate*4)/(r['prior_skill_count']+4)

def save(model,path):
    Path(path).write_text(json.dumps(model,ensure_ascii=False,indent=2))

def load(path):
    model=json.loads(Path(path).read_text());assert model['type']=='logistic_sgd';return model
