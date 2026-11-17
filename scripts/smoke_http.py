"""Run after FastAPI and Streamlit start in ordinary Ubuntu; no model training."""
import argparse
import json
import statistics
import time
import sys
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.api.contracts import TRAJECTORY_CONTRACT_VERSION, validate_trajectory

def check(base,ui,student=None,require_fastapi=True):
    base=base.rstrip('/');ui=ui.rstrip('/');session=requests.Session();timings=[]
    def get(path,expected=200):
        started=time.perf_counter();response=session.get(base+path,timeout=15)
        timings.append({'path':path,'ms':round((time.perf_counter()-started)*1000,3),'status':response.status_code})
        assert response.status_code==expected,(path,response.status_code,response.text[:300])
        return response
    health=get('/health').json();assert health['status']=='ok' and 'ASSISTments' in health['dataset']
    assert health.get('trajectory_contract_version')==TRAJECTORY_CONTRACT_VERSION, 'Restart the old API process: incompatible contract'
    docs=get('/docs');assert 'swagger-ui' in docs.text.lower() if require_fastapi else '/health' in docs.text
    if require_fastapi:
        spec=get('/openapi.json').json()
        assert spec['info']['title']=='EduPath ML'
        for path in ['/health','/students','/students/{user_id}/profile','/students/{user_id}/trajectory','/skills','/materials','/model/info']:
            assert path in spec['paths'],path
    students=get('/students?limit=3').json();assert students and isinstance(students[0],str)
    uid=student or students[0]
    skills=get('/skills').json();assert len(skills)==149
    profile=get(f'/students/{uid}/profile').json()
    assert profile['user_id']==uid and profile['responses']>0 and len(profile['skills'])==149
    assert all(0<=x['predicted_probability']<=1 for x in profile['skills'])
    route_result=validate_trajectory(get(f'/students/{uid}/trajectory').json());route=route_result['trajectory']
    assert route and all(x['reason'] and x['material'] for x in route)
    assert route_result['material_count']==23
    catalog=get('/materials?limit=50').json()
    assert len(catalog)==23 and all(m['learning_goal'] and m['practice_exercises'] for m in catalog)
    for other_uid, expected_ids in [('79021',['292','290','2_37_70','39','299']),('75169',['292','9_12']),('78970',['16_17','290','17','294'])]:
        other=validate_trajectory(get(f'/students/{other_uid}/trajectory').json())
        assert [x['skill_id'] for x in other['trajectory']]==expected_ids
    assert route_result['detected_difficulties']
    if uid=='79021':
        assert len(route)==5
        assert set(route_result['focus_skill_ids'])=={'292','299','290','2_37_70'}
        assert '76' in {x['skill_id'] for x in route_result['without_materials']}
        assert any('Повороты' in x['skill_name'] for x in route)
    positions={x['skill_id']:i for i,x in enumerate(route)}
    assert all(positions[parent]<i for i,x in enumerate(route) for parent in x['prerequisites'])
    first=route[0];material=get(f"/materials?skill={first['skill_id']}").json()
    assert material and material[0]['skill_id']==first['skill_id']
    assert material[0]['explanation'] and material[0]['url'].startswith('https://openstax.org/')
    info=get('/model/info').json();assert info['split_user_overlap']==0
    assert info['metrics']['logistic_sgd']['roc_auc']>.7
    get('/students/not-a-student/profile',404)
    get('/students?limit=0',422)
    no_history=get('/students/21825/trajectory').json()
    assert no_history['trajectory']==[] and not no_history['focus_skill_ids']
    ui_response=session.get(ui+'/_stcore/health',timeout=15)
    assert ui_response.status_code==200,('Streamlit health',ui_response.status_code,ui_response.text[:100])
    ui_root=session.get(ui+'/',timeout=15)
    assert ui_root.status_code==200 and 'streamlit' in ui_root.text.lower()
    result={'api_base':base,'streamlit_base':ui,'student':uid,'profile_skills':len(profile['skills']),
            'contract_version':route_result['contract_version'],'route_skills':len(route),'first_route_skill':first['skill_name'],
            'material':material[0]['title'],'docs':'Swagger verified' if require_fastapi else 'fallback docs verified',
            'streamlit_health':'ok','requests':timings,
            'api_request_median_ms':round(statistics.median(x['ms'] for x in timings),3)}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--api',default='http://127.0.0.1:8000')
    p.add_argument('--ui',default='http://127.0.0.1:8501')
    p.add_argument('--student',default='79021')
    p.add_argument('--allow-fallback',action='store_true',help='Accept plain fallback docs instead of FastAPI Swagger')
    args=p.parse_args();result=check(args.api,args.ui,args.student,not args.allow_fallback)
    out=ROOT/'reports/http_integration.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
