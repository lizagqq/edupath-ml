"""Record reproducible retrieval and route checks; draw a package-free SVG chart."""
import json
import sys
import io
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.api.service import Service
from src.retrieval.materials import search,MATERIALS,REAL_MATERIALS
from scripts.smoke_server import Handler

s=Service();ids=s.students(3)
real=s.info()['dataset'].startswith('ASSISTments')
if real:
    materials=REAL_MATERIALS
    queries=[('сложение дробей','280'),('как умножить дроби','67'),('деление на дробь','61'),
             ('перевести дробь в процент','47'),('какой процент составляет часть','77'),
             ('вычислить процент от числа','70'),('решить пропорцию','79'),
             ('уравнение два действия','311'),('уравнение со скобками','312')]
else:
    materials=MATERIALS
    queries=[('дроби','fractions'),('десятичные дроби','decimals'),('проценты','percent'),
             ('отношения','ratio'),('пропорции','proportion'),('линейные уравнения','equations'),
             ('геометрия','geometry'),('площадь фигур','area')]
cases=[{'query':q,'expected':skill,'found':search(q,limit=1,materials=materials)[0]['skill_id']} for q,skill in queries]
routes={uid:[x['skill_id'] for x in s.trajectory(uid)['trajectory']] for uid in ids}
result={'dataset':s.info()['dataset'],'retrieval_cases':cases,
        'hit_at_1':sum(x['expected']==x['found'] for x in cases)/len(cases),
        'routes':routes,'distinct_routes':len({tuple(v) for v in routes.values()})}
times=[]
for _ in range(30):
    h=Handler.__new__(Handler);h.path=f'/students/{ids[0]}/trajectory';h.wfile=io.BytesIO()
    h.send_response=lambda code:None;h.send_header=lambda key,value:None;h.end_headers=lambda:None
    start=time.perf_counter();h.do_GET();times.append((time.perf_counter()-start)*1000)
times.sort();result['in_process_api_dispatch_ms']={'median':round(times[len(times)//2],3),
                                                     'p95':round(times[int(.95*(len(times)-1))],3),
                                                     'note':'Direct handler call; excludes HTTP transport because sandbox denies sockets.'}
(ROOT/'reports/system_evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
metrics=s.info()['metrics'];names=list(metrics);colors=['#94a3b8','#38bdf8','#0f766e']
lines=['<svg xmlns="http://www.w3.org/2000/svg" width="720" height="300" viewBox="0 0 720 300">',
       '<rect width="720" height="300" fill="white"/><text x="20" y="30" font-size="20">Log loss: меньше — лучше</text>']
for i,name in enumerate(names):
    y=65+i*68;value=metrics[name]['log_loss'];width=value*600
    lines.extend([f'<text x="20" y="{y+18}" font-size="15">{name}</text>',
                  f'<rect x="175" y="{y}" width="{width:.1f}" height="27" fill="{colors[i]}"/>',
                  f'<text x="{185+width:.1f}" y="{y+19}" font-size="15">{value:.3f}</text>'])
lines.append('</svg>')
(ROOT/'reports/figures/log_loss.svg').write_text('\n'.join(lines))
print(json.dumps(result,ensure_ascii=False,indent=2))
