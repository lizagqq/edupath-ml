"""Heuristic priority and prerequisite order for a small manually curated graph."""
from collections import defaultdict,deque

EDGES=[('fractions','decimals'),('fractions','percent'),('ratio','proportion'),('fractions','equations'),('geometry','area')]
REAL_EDGES=[('67','61'),('47','77'),('47','70'),('311','312'),('39','299')]

def topological(skills,edges=EDGES):
    skills=set(skills);indeg={s:0 for s in skills};children=defaultdict(list)
    # NetworkX is used when available; the same DAG check has a stdlib fallback.
    try:
        import networkx as nx
        graph=nx.DiGraph();graph.add_nodes_from(skills)
        graph.add_edges_from((a,b) for a,b in edges if a in skills and b in skills)
        if not nx.is_directed_acyclic_graph(graph):raise ValueError('Prerequisite cycle')
    except ImportError:
        pass
    for a,b in edges:
        if a in skills and b in skills:indeg[b]+=1;children[a].append(b)
    ready=deque(sorted(s for s,n in indeg.items() if n==0));out=[]
    while ready:
        s=ready.popleft();out.append(s)
        for b in sorted(children[s]):
            indeg[b]-=1
            if indeg[b]==0:ready.append(b)
    if len(out)!=len(skills):raise ValueError('Prerequisite cycle')
    return out

def rank(profile,materials,edges=EDGES):
    """Low predicted success and scarce evidence drive transparent priorities."""
    byid={x['skill_id']:x for x in profile};parents=defaultdict(list)
    for a,b in edges:
        if a in byid and b in byid:parents[b].append(a)
    ordered=topological(byid,edges);out=[]
    for sid in ordered:
        x=byid[sid];p=x.get('predicted_probability')
        if p is None:p=.5
        count=x['observations'];reason=[]
        if count<3:reason.append('недостаточно данных')
        if p<.6:reason.append('низкая прогнозируемая вероятность')
        pending=[a for a in parents[sid] if byid[a].get('predicted_probability',.5)<.65 or byid[a]['observations']<3]
        if pending:reason.append('сначала повторить предварительный навык: '+', '.join(byid[a]['skill_name'] for a in pending))
        priority=round((1-p)*100 + (15 if count<3 else 0) + (8 if pending else 0),1)
        out.append({'skill_id':sid,'skill_name':x['skill_name'],'priority':priority,
                    'reason':'; '.join(reason) or 'плановое закрепление',
                    'prerequisites':parents[sid],
                    'material':next((m for m in materials if m['skill_id']==sid),None)})
    # Respect edges even when an advanced skill has a higher raw priority.
    result=[];remaining={x['skill_id']:x for x in out}
    while remaining:
        ready=[x for x in remaining.values() if all(a not in remaining for a in x['prerequisites'])]
        if not ready:raise ValueError('Prerequisite cycle')
        chosen=max(ready,key=lambda x:(x['priority'],x['skill_id']))
        result.append(chosen);del remaining[chosen['skill_id']]
    return result


MIN_DIAGNOSTIC_ANSWERS = 3
WEAK_FORECAST = .5
MAX_FOCUS = 4
MAX_REINFORCEMENT = 3


def evidence_note(observations):
    """Even a very low forecast from three answers is only an early signal."""
    if observations < MIN_DIAGNOSTIC_ANSWERS:
        return f'недостаточно данных: {observations} ответ(а)'
    if observations < 10:
        return f'предварительный сигнал: только {observations} ответ(а)'
    return f'основано на {observations} ответах; прогноз не является диагнозом освоения'


def personalized_plan(profile,materials,edges=REAL_EDGES):
    """Select diagnosed weak skills first; add only needed prerequisites.

    IDs stay distinct. A shared source label is used only to avoid showing
    duplicate concept cards in the short *main* route; every ID remains in
    the diagnosis and can appear in optional reinforcement.
    """
    byid={x['skill_id']:x for x in profile}
    material_byid={m['skill_id']:m for m in materials}
    parents=defaultdict(list)
    for parent,child in edges:
        if parent in byid and child in byid:
            parents[child].append(parent)

    diagnosed=sorted((x for x in profile
                      if x['observations']>=MIN_DIAGNOSTIC_ANSWERS
                      and x['predicted_probability']<WEAK_FORECAST),
                     key=lambda x:(x['predicted_probability'],-x['observations'],x['skill_id']))
    supported=[x for x in diagnosed if x['skill_id'] in material_byid]
    focus=[];seen_labels=set()
    for x in supported:
        # ASSISTments has several different Circle Graph IDs. Their scores
        # are never combined; only one shared reading enters the short route.
        label=x.get('dataset_skill_name') or x['skill_name']
        key=label if label and label!=x['skill_id'] else x['skill_id']
        if key in seen_labels:continue
        seen_labels.add(key);focus.append(x)
        if len(focus)==MAX_FOCUS:break
    focus_ids={x['skill_id'] for x in focus}
    selected=set(focus_ids)
    prerequisite_ids=set()

    def add_needed(parent):
        if parent in selected or parent not in material_byid:return
        x=byid[parent]
        if x['observations']>=MIN_DIAGNOSTIC_ANSWERS and x['predicted_probability']>=.7:
            return
        selected.add(parent);prerequisite_ids.add(parent)
        for ancestor in parents[parent]:add_needed(ancestor)

    for x in focus:
        for parent in parents[x['skill_id']]:add_needed(parent)

    chosen=[{**byid[sid],'skill_name':byid[sid]['display_name']}
            for sid in selected]
    ordered=rank(chosen,materials,edges) if chosen else []
    children=defaultdict(list)
    for parent,child in edges:
        if child in focus_ids and parent in prerequisite_ids:children[parent].append(child)
    steps=[]
    for item in ordered:
        sid=item['skill_id'];x=byid[sid];role='prerequisite' if sid in prerequisite_ids else 'focus'
        if role=='prerequisite':
            targets=', '.join(byid[child]['display_name'] for child in children[sid])
            reason=f'Нужно перед темой «{targets}»; без этого шага переход к ней может быть преждевременным.'
        else:
            reason=(f'Выявлено затруднение: прогноз правильного следующего ответа '
                    f'{x["predicted_probability"]*100:.0f}% при {x["observations"]} ответах.')
        steps.append({**item,'role':role,'reason':reason,
                      'predicted_probability':x['predicted_probability'],
                      'observed_accuracy':x['observed_accuracy'],
                      'observations':x['observations'],
                      'evidence_note':evidence_note(x['observations']),
                      'dataset_skill_name':x.get('dataset_skill_name',x['skill_name']),
                      'all_prerequisites':parents[sid]})

    def summary(x):
        return {'skill_id':x['skill_id'],'skill_name':x['display_name'],
                'dataset_skill_name':x.get('dataset_skill_name',x['skill_name']),
                'observations':x['observations'],
                'observed_accuracy':x['observed_accuracy'],
                'predicted_probability':x['predicted_probability'],
                'evidence_note':evidence_note(x['observations']),
                'material_available':x['skill_id'] in material_byid,
                'material':material_byid.get(x['skill_id'])}

    without=[summary(x) for x in diagnosed if x['skill_id'] not in material_byid]
    remainder=[x for x in supported if x['skill_id'] not in selected]
    reinforcement=[summary(x) for x in remainder[:MAX_REINFORCEMENT]]
    if not diagnosed:
        note='По навыкам с минимум тремя ответами не выявлено низких прогнозов; маршрут не сформирован.'
    elif not focus:
        note='Затруднения выявлены, но материалы для них пока не подготовлены; общий каталог не выдаётся за личный маршрут.'
    else:
        note=(f'Основных тем с выявленными затруднениями: {len(focus)}; '
              f'необходимых предварительных тем: {len(prerequisite_ids)}.')
    return {'trajectory':steps,'trajectory_note':note,
            'detected_difficulties':[summary(x) for x in diagnosed],
            'without_materials':without,'reinforcement':reinforcement,
            'focus_skill_ids':[x['skill_id'] for x in focus],
            'prerequisite_skill_ids':sorted(prerequisite_ids),
            'material_count':len(materials),
            'selection_rule':f'Прогноз < {WEAK_FORECAST:.0%}, минимум {MIN_DIAGNOSTIC_ANSWERS} ответа; '
                             f'до {MAX_FOCUS} разных тем с материалами, затем нужные предварительные темы.'}
