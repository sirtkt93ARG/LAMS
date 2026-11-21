import unittest

from matheval.rubrics import competencies_for_item, rubric_snapshot


class TestCompetencyRubrics(unittest.TestCase):
    def test_snapshot_has_stable_five_level_descriptors(self):
        competencies = competencies_for_item("T3-01")
        self.assertTrue(competencies)
        snapshot = rubric_snapshot(competencies[0]["id"])
        self.assertEqual(snapshot["competency_id"], competencies[0]["id"])
        self.assertEqual(len(snapshot["criteria"]), 3)
        for criterion in snapshot["criteria"]:
            self.assertEqual(set(criterion["descriptors"]), {"0", "1", "2", "3", "4"})

    def test_unknown_competency_has_no_rubric(self):
        self.assertIsNone(rubric_snapshot("competencia_inexistente"))


if __name__ == "__main__":
    unittest.main()
