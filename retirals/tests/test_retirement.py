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
        self.assertGreater(metrics["minimum_corpus_required"], 0)

        retirement_row = next(row for row in result["projections"] if row["age"] == 54)
        self.assertAlmostEqual(retirement_row["closing"], 45652531.53, places=2)
        self.assertAlmostEqual(retirement_row["ltcg_tax"], 155221.87, places=2)

    def test_supports_custom_adhoc_expenses(self):
        result = calculate_retirement(PlannerInputs(
            current_age=23,
            retirement_age=58,
            life_expectancy=85,
            current_annual_expenses=600000.0,
            avg_inflation_rate=0.06,
            current_corpus=100000.0,
            annual_contribution=200000.0,
            adhoc_expenses=[
                {"age": 58, "amount": 2500000.00},
                {"age": 75, "amount": 1000000.00},
            ],
        ))

        retirement_row = next(row for row in result["projections"] if row["age"] == 58)
        expected_ad_hoc = 2500000.00 * ((1 + 0.06) ** (58 - 23))
        self.assertAlmostEqual(retirement_row["ad_hoc"], expected_ad_hoc, places=2)
        self.assertGreater(result["metrics"]["minimum_corpus_required"], 0)

    def test_rejects_invalid_age_configuration(self):
        with self.assertRaises(ValueError):
            calculate_retirement(PlannerInputs(current_age=60, retirement_age=58, life_expectancy=85))


if __name__ == "__main__":
    unittest.main()
