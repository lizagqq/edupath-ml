"""Check UI meaning against the existing real-data service without Streamlit."""

import unittest

from src.api.service import Service
from ui.presentation import (
    SOURCE_TRANSLATIONS, bar, percent, prediction_explanation, risk,
    route_position_explanation, skill_label, split_skills,
)


class PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = Service()

    def test_source_labels_and_unknown_names(self):
        with self.service._db() as db:
            source_names = {row[0] for row in db.execute("SELECT skill_name FROM skills")}
        self.assertTrue(set(SOURCE_TRANSLATIONS) <= source_names)
        profile = self.service.profile("79021")
        by_id = {skill["skill_id"]: skill for skill in profile["skills"]}
        self.assertEqual(skill_label(by_id["292"]), ("Повороты фигур", False))
        self.assertEqual(skill_label(by_id["76"]), ("Навык ID 76", True))
        self.assertEqual(skill_label(by_id["110"]), ("Навык ID 110", True))
        self.assertIn("Описание навыка", prediction_explanation(by_id["76"]))
        self.assertEqual(skill_label(by_id["47"])[0], "Перевод дробей, десятичных дробей и процентов")

    def test_observed_skill_counts_exclude_unseen(self):
        profile = self.service.profile("79021")
        enough, sparse, unseen = split_skills(profile["skills"])
        self.assertEqual((len(enough), len(sparse), len(unseen)), (56, 37, 56))
        self.assertEqual(len(enough) + len(sparse), 93)
        self.assertEqual(len(profile["skills"]), 149)
        self.assertTrue(all(s["observations"] >= 3 for s in enough))
        self.assertTrue(all(s["observations"] == 0 for s in unseen))

    def test_risk_and_separate_observed_vs_predicted(self):
        self.assertEqual(risk(0.49)[0], "Высокий риск")
        self.assertEqual(risk(0.5)[0], "Умеренный риск")
        self.assertEqual(risk(0.7)[0], "Низкий риск")
        self.assertEqual(percent(None), "—")
        skill = next(s for s in self.service.profile("79021")["skills"] if s["skill_id"] == "292")
        self.assertNotEqual(percent(skill["observed_accuracy"]), percent(skill["predicted_probability"]))
        self.assertIn("следующего ответа", prediction_explanation(skill))

    def test_route_explanation_and_safe_bar_labels(self):
        profile = self.service.profile("79021")
        names = {skill["skill_id"]: skill_label(skill)[0] for skill in profile["skills"]}
        route = self.service.trajectory("79021")["trajectory"]
        dependent = next(item for item in route if item["prerequisites"])
        note = route_position_explanation(dependent, route.index(dependent) + 1, names)
        self.assertIn(names[dependent["prerequisites"][0]], note)
        self.assertIn("баллом приоритета", note)
        html = bar("<Очень длинное название>", .756, display="0,756")
        self.assertIn("&lt;Очень длинное название&gt;", html)
        self.assertIn("0,756", html)
        self.assertNotIn("<Очень длинное название>", html)


if __name__ == "__main__":
    unittest.main()
