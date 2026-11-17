"""ASSISTments CSV loader and clearly synthetic fallback."""
import csv
import math
import random
from collections import Counter
from pathlib import Path

SKILLS = [
    ("fractions", "Дроби"), ("decimals", "Десятичные дроби"),
    ("percent", "Проценты"), ("ratio", "Отношения"),
    ("proportion", "Пропорции"), ("equations", "Линейные уравнения"),
    ("geometry", "Геометрия"), ("area", "Площадь фигур"),
]

def synthetic_events(students=240, seed=42):
    """A simulation for software validation, never for scientific claims."""
    rng=random.Random(seed)
    rows=[]
    for u in range(students):
        ability=rng.gauss(0, .85)
        focus=u % len(SKILLS)
        counts=Counter()
        for order in range(55):
            k=focus if rng.random()<.55 else rng.randrange(len(SKILLS))
            sid,name=SKILLS[k]
            z=ability + (counts[sid]*.055) - (k%4)*.27 - .35
            p=1/(1+math.exp(-z))
            correct=int(rng.random()<p)
            rows.append(dict(user_id=f"demo-{u:04d}",skill_id=sid,
                             skill_name=name,order_id=order,correct=correct))
            counts[sid]+=1
    return rows

def load_assistments(path):
    """Read the corrected single-row-per-problem CSV when supplied by the user."""
    # Five malformed UTF-8 bytes occur in answer_text in the supplied CSV;
    # answer_text is never used for features or targets.
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f:
        reader=csv.DictReader(f)
        names=set(reader.fieldnames or [])
        required={'user_id','correct'}
        if not required <= names or not ({'skill_id','skill_name'} & names):
            raise ValueError(f"Expected {required} and skill_id/skill_name; got {sorted(names)}")
        order='order_id' if 'order_id' in names else None
        if not order: raise ValueError('order_id is required for a causal sequence')
        rows=[];rejected=Counter()
        null={'','na','nan','none','null'}
        for i,r in enumerate(reader):
            uid=(r.get('user_id') or '').strip()
            raw_id=(r.get('skill_id') or '').strip()
            raw_name=(r.get('skill_name') or '').strip()
            skill=raw_id if raw_id.lower() not in null else raw_name
            name=raw_name if raw_name.lower() not in null else skill
            try:
                target_value=float(r['correct']);orderv=float(r[order])
            except (ValueError,TypeError): rejected['bad_target_or_order']+=1;continue
            if uid.lower() in null or skill.lower() in null or target_value not in (0.,1.) or not math.isfinite(orderv):
                rejected['missing_or_invalid']+=1;continue
            target=int(target_value)
            rows.append(dict(user_id=uid,skill_id=skill,skill_name=name,
                             order_id=orderv,correct=target,_source_row=i))
    rows.sort(key=lambda r:(r['user_id'],r['order_id'],r['_source_row']))
    return rows,dict(rejected)

def describe(rows):
    return {'responses':len(rows),'students':len({r['user_id'] for r in rows}),
            'skills':len({r['skill_id'] for r in rows}),
            'correct_rate':sum(r['correct'] for r in rows)/len(rows) if rows else None}
