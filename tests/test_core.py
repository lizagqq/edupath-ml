import csv
import json
import tempfile
import unittest
from pathlib import Path
from src.data.dataset import load_assistments,synthetic_events
from src.ml.model import features,group_split,train_logistic,predict,auc
from src.recommendation.trajectory import topological,rank,personalized_plan,EDGES
from src.retrieval.materials import search,MATERIALS,REAL_MATERIALS,REAL_SOURCE_NAMES
from src.api.service import Service

class DataTests(unittest.TestCase):
    def test_loader_schema_and_invalid_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'small.csv'
            p.write_text('user_id,skill_id,correct,order_id\nu1,fractions,1,1\nu1,fractions,0.5,2\nu2,NA,1,3\n')
            rows,rejected=load_assistments(p)
            self.assertEqual(len(rows),1);self.assertEqual(rejected['missing_or_invalid'],2)
            p.write_text('user_id,correct\nu1,1\n')
            with self.assertRaises(ValueError):load_assistments(p)
    def test_future_answer_does_not_change_past_features(self):
        rows=[dict(user_id='a',skill_id='s',order_id=i,correct=v) for i,v in enumerate([1,0,1])]
        before=features(rows);rows[-1]['correct']=0;after=features(rows)
        keys=['prior_count','prior_success','prior_skill_count','prior_skill_success']
        self.assertEqual([[r[k] for k in keys] for r in before],[[r[k] for k in keys] for r in after])
        self.assertEqual(before[0]['prior_skill_count'],0)
    def test_split_and_probability(self):
        rows=features(synthetic_events(30));train,test=group_split(rows)
        self.assertFalse({r['user_id'] for r in train}&{r['user_id'] for r in test})
        model=train_logistic(train,epochs=2)
        self.assertTrue(all(0<=predict(model,r)<=1 for r in test[:100]))
    def test_auc_ties(self):self.assertAlmostEqual(auc([0,1,0,1],[.4]*4),.5)

class RecommendationTests(unittest.TestCase):
    def test_graph_cycle_and_order(self):
        order=topological(['fractions','equations'],EDGES)
        self.assertLess(order.index('fractions'),order.index('equations'))
        with self.assertRaises(ValueError):topological(['a','b'],[('a','b'),('b','a')])
    def test_low_data_and_prerequisites(self):
        p=[{'skill_id':'fractions','skill_name':'Дроби','observations':1,'predicted_probability':.3},
           {'skill_id':'equations','skill_name':'Уравнения','observations':10,'predicted_probability':.2}]
        result=rank(p,MATERIALS)
        self.assertEqual([x['skill_id'] for x in result],['fractions','equations'])
        self.assertIn('недостаточно данных',result[0]['reason'])
    def test_retrieval(self):
        self.assertEqual(search('проценты')[0]['skill_id'],'percent')
        self.assertEqual(search(skill='fractions')[0]['skill_id'],'fractions')
        self.assertEqual(search(skill='unknown'),[])
        self.assertEqual(search('решить пропорцию',materials=REAL_MATERIALS)[0]['skill_id'],'79')
    def test_personalized_plan_needs_diagnosis_and_explains_prerequisite(self):
        docs=[{'skill_id':sid,'title':sid} for sid in ('base','target')]
        profile=[{'skill_id':'base','skill_name':'Основа','display_name':'Основа',
                  'observations':12,'observed_accuracy':.7,'predicted_probability':.65},
                 {'skill_id':'target','skill_name':'Цель','display_name':'Цель',
                  'observations':8,'observed_accuracy':.25,'predicted_probability':.2}]
        result=personalized_plan(profile,docs,[('base','target')])
        self.assertEqual([x['skill_id'] for x in result['trajectory']],['base','target'])
        self.assertEqual(result['trajectory'][0]['role'],'prerequisite')
        self.assertIn('перед темой',result['trajectory'][0]['reason'])
        profile[1]['observations']=2
        self.assertEqual(personalized_plan(profile,docs,[('base','target')])['trajectory'],[])

class ServiceTests(unittest.TestCase):
    def setUp(self):self.s=Service()
    def test_profiles_and_distinct_routes(self):
        self.assertTrue(self.s.ready())
        ids=self.s.students(3)
        routes=[tuple(x['skill_id'] for x in self.s.trajectory(uid)['trajectory']) for uid in ids]
        self.assertEqual(len(set(routes)),3)
        self.assertGreater(self.s.profile(ids[0])['responses'],0)
        with self.assertRaises(KeyError):self.s.profile('missing')
    def test_health_and_materials(self):
        self.assertEqual(self.s.health()['status'],'ok')
        skill='47' if self.s.info()['dataset'].startswith('ASSISTments') else 'percent'
        self.assertTrue(self.s.materials(skill=skill))
        if self.s.info()['dataset'].startswith('ASSISTments'):
            prompt=self.s.materials(skill='292')[0]
            self.assertIn('practice_question',prompt)
            self.assertIn('practice_answer',prompt)
    def test_saved_model_excludes_current_response_fields(self):
        from src.ml.model import load
        model=load(self.s.model_path)
        self.assertFalse({'correct','attempt_count','hint_count'} & set(model['features']))
        profile=self.s.profile(self.s.students(1)[0])
        self.assertTrue(all(0<=x['predicted_probability']<=1 for x in profile['skills']))
    def test_no_supported_skill_history_has_no_personal_route(self):
        if not self.s.info()['dataset'].startswith('ASSISTments'):self.skipTest('Real dataset coverage check')
        with self.s._db() as db:
            uid=db.execute('''SELECT s.user_id FROM students s WHERE NOT EXISTS
                (SELECT 1 FROM interactions i WHERE i.user_id=s.user_id
                 AND i.skill_id IN (SELECT skill_id FROM materials)) LIMIT 1''').fetchone()[0]
        route=self.s.trajectory(uid)
        self.assertEqual(route['trajectory'],[])
        self.assertEqual(route['focus_skill_ids'],[])
        self.assertTrue(route['trajectory_note'])
    def test_real_diagnosis_drives_short_distinct_routes(self):
        if not self.s.info()['dataset'].startswith('ASSISTments'):self.skipTest('Real dataset route')
        routes={uid:self.s.trajectory(uid) for uid in ('79021','75169','78970')}
        self.assertEqual([len(routes[uid]['trajectory']) for uid in routes],[5,2,4])
        first=routes['79021']
        self.assertEqual(set(first['focus_skill_ids']),{'292','299','290','2_37_70'})
        self.assertEqual(first['prerequisite_skill_ids'],['39'])
        self.assertNotIn('79',{x['skill_id'] for x in first['trajectory']})
        self.assertIn('76',{x['skill_id'] for x in first['without_materials']})
        positions={x['skill_id']:i for i,x in enumerate(first['trajectory'])}
        self.assertLess(positions['39'],positions['299'])
        self.assertIn('предварительный сигнал',next(x for x in first['trajectory'] if x['skill_id']=='292')['evidence_note'])
        self.assertEqual(len({tuple(x['skill_id'] for x in route['trajectory']) for route in routes.values()}),3)
    def test_circle_graph_ids_remain_distinct(self):
        profile=self.s.profile('79021')
        circle=[x for x in profile['skills'] if x['skill_name']=='Circle Graph']
        self.assertGreaterEqual(len(circle),4)
        self.assertEqual(len({x['skill_id'] for x in circle}),len(circle))
        route=self.s.trajectory('79021')
        diagnosed={x['skill_id'] for x in route['detected_difficulties']}
        self.assertTrue({'2_37_70','2_37_48_77'} <= diagnosed)
        self.assertIn('2_37_48_77',{x['skill_id'] for x in route['reinforcement']})
        with self.s._db() as db:
            names=dict(db.execute('SELECT skill_id,skill_name FROM skills'))
        self.assertTrue(all(names[sid]==label for sid,label in REAL_SOURCE_NAMES.items()))

if __name__=='__main__':unittest.main()
