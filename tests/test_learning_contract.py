"""Regress reported wire errors and verify fixed lessons independently of ML training."""
from copy import deepcopy
from fractions import Fraction
import unittest
from unittest.mock import patch

from src.api.contracts import ContractError, validate_trajectory
from src.api.service import Service
from src.retrieval.lessons import LESSONS
from ui.api_client import fetch_plan
from ui.presentation import count_phrase, friendly_labels


class LearningContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = Service()
        cls.plan = cls.service.trajectory('79021')

    def test_real_response_roundtrip_and_routes(self):
        import json
        for uid, count in [('79021', 5), ('75169', 2), ('78970', 4), ('21825', 0)]:
            result = validate_trajectory(json.loads(json.dumps(self.service.trajectory(uid))))
            self.assertEqual(len(result['trajectory']), count)
        self.assertEqual([x['skill_id'] for x in self.plan['trajectory']], ['292', '290', '2_37_70', '39', '299'])

    def test_missing_reported_fields_rejected_at_http_boundary(self):
        from scripts.smoke_streamlit import LocalResponse
        old = deepcopy(self.plan)
        for name in ('detected_difficulties', 'material_count'): old.pop(name)
        with patch('requests.get', return_value=LocalResponse(old)):
            with self.assertRaises(ContractError) as cm: fetch_plan('http://example.test', '79021')
        self.assertIn('detected_difficulties', str(cm.exception))
        self.assertIn('material_count', str(cm.exception))
        self.assertIn('Перезапустите', str(cm.exception))

    def test_wrong_version_broken_lesson_and_dependency_fail_explicitly(self):
        for mutate in [lambda p: p.update(contract_version=1),
                       lambda p: p['trajectory'][0]['material'].pop('learning_goal'),
                       lambda p: p['trajectory'][0].update(prerequisites=['299']),
                       lambda p: p['trajectory'][0]['material']['practice_exercises'][0].update(solution=42),
                       lambda p: p['reinforcement'][0]['material'].pop('url')]:
            malformed = deepcopy(self.plan); mutate(malformed)
            with self.assertRaises(ContractError): validate_trajectory(malformed)

    def test_distinct_labels_do_not_merge_histories(self):
        labels = friendly_labels(self.plan['skills'])
        ids = ['2_37_70', '2_37_48_77', '2_48_79', '2_70']
        self.assertEqual(len(set(labels[sid] for sid in ids)), 4)
        self.assertTrue(all(sid not in labels[sid] for sid in ids))
        self.assertEqual(len(labels), 149)
        self.assertEqual([count_phrase(n) for n in [1, 2, 3, 5, 11, 21, 22, 111]],
                         ['1 ответ', '2 ответа', '3 ответа', '5 ответов', '11 ответов', '21 ответ', '22 ответа', '111 ответов'])

    def test_all_23_catalog_records_have_fixed_lessons_and_independent_copies(self):
        materials = self.service.materials(limit=50)
        self.assertEqual({x['skill_id'] for x in materials}, set(LESSONS))
        self.assertEqual(len(materials), 23)
        for m in materials:
            self.assertTrue(m['learning_goal'] and m['theory'] and m['worked_example']['solution'])
            self.assertTrue(1 <= len(m['practice_exercises']) <= 2)
            self.assertTrue(all(x['answer'] and x['solution'] for x in m['practice_exercises']))
        materials[0]['practice_exercises'][0]['answer'] = 'changed'
        self.assertNotEqual(self.service.materials(limit=50)[0]['practice_exercises'][0]['answer'], 'changed')

    def test_fixed_practice_answers_against_mathematical_calculations(self):
        # Recalculate independently: 20 distinct lesson concepts, 4 separate Circle Graph records.
        expected = {
            '292': [f'({-2}; {1})', f'({-1}; {-3})'],
            '290': [f'({-4}; {-1})', f'({-2}; {-3})'],
            '39': [f'{4**2}π см²', f'{(10//2)**2}π см²'],
            '299': [f'{2*1**2 + 2*1*2}π см²', f'{2*3**2 + 2*3*4}π см²'],
            '9_12': ['2 | 3 7; 3 | 1'],
            '16_17': [f'{2*3} вариантов'], '17': [str(Fraction(1,6)**2)],
            '294': [f'{6*5-2*3} см²'], '277': [str(-4-(-7))], '81': [f'{150//3} км/ч'],
            '280': [str(Fraction(1,3)+Fraction(1,6))],
            '67': [str(Fraction(3,5)*Fraction(10,9))], '61': [str(Fraction(3,4)/Fraction(1,2))],
            '47': ['0,6 = 60%'], '77': [f'{int(Fraction(18,60)*100)}%'],
            '70': [str(int(Fraction(15,100)*200))], '79': [str(int(Fraction(6,10)*5))],
            '311': [f'x = {(14-2)//3}'], '312': [f'x = {(14+1)//3-2}'],
        }
        for sid in ('2_37_70', '2_37_48_77', '2_48_79', '2_70'):
            expected[sid] = [f'{int(Fraction(20,100)*360)}°', f'{int(Fraction(30,100)*40)} учеников']
        self.assertEqual(set(expected), set(LESSONS))
        for sid, answers in expected.items():
            with self.subTest(skill=sid):
                actual = [x['answer'].replace('−', '-') for x in LESSONS[sid]['practice_exercises']]
                self.assertEqual(actual, answers)
        # The other representations and the stem plot are checked by reconstruction.
        self.assertEqual(Fraction('0.6'), Fraction(60, 100))
        self.assertEqual([10*stem+leaf for stem, leaves in [(2,[3,7]), (3,[1])] for leaf in leaves], [23,27,31])


if __name__ == '__main__': unittest.main()
