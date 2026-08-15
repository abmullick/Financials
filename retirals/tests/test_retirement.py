import unittest

from src.main import PlannerInputs, calculate_retirement


class RetirementPlannerWorkbookParityTest(unittest.TestCase):
    def test_matches_default_workbook_behavior(self):
        result = calculate_retirement(PlannerInputs())
        metrics = result["metrics"]

        self.assertAlmostEqual(metrics["corpus_at_retirement"], 42131033.64, places=2)
        self.assertAlmostEqual(metrics["final_corpus"], 1536805609.0, places=0)
        self.assertEqual(metrics["years_in_retirement"], 36)
        self.assertEqual(metrics["peak_age"], 58)
        self.assertAlmostEqual(metrics["total_contributions"], 8096784.27, places=2)

        retirement_row = next(row for row in result["projections"] if row["age"] == 54)
        self.assertAlmostEqual(retirement_row["closing"], 45652531.53, places=2)
        self.assertAlmostEqual(retirement_row["ltcg_tax"], 155221.87, places=2)


if __name__ == "__main__":
    unittest.main()
