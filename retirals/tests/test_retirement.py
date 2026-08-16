import unittest
from src.models import PlannerInputs, AdHocExpense, StressScenario
from src.main import calculate_retirement

class RetirementPlannerTest(unittest.TestCase):
    """Comprehensive test suite for the retirement planner engine."""

    def test_normal_projection_and_workbook_parity(self):
        """
        Validates a standard projection and maintains parity with the original
        workbook values for a high-return scenario.
        """
        inputs = PlannerInputs(
            pre_retirement_return=0.16, 
            post_retirement_return=0.15,
            adhoc_expenses=[
                AdHocExpense(age=58, amount=2500000.00),
                AdHocExpense(age=75, amount=1000000.00)
            ]
        )
        result = calculate_retirement(inputs)
        metrics = result["metrics"]

        # Key metric validation
        self.assertAlmostEqual(metrics["corpus_at_retirement"], 42131033.64, places=2)
        self.assertAlmostEqual(metrics["final_corpus"], 893537171.0, places=0, msg="Final corpus should match workbook.")
        self.assertEqual(metrics["retirement_duration_years"], 36)
        self.assertEqual(metrics["peak_age"], 58)
        self.assertAlmostEqual(metrics["total_contributions"], 8096784.27, places=2)
        self.assertGreater(metrics["minimum_corpus_required"], 0, "Minimum corpus must be calculated.")

        # Spot check a specific projection row for accuracy
        retirement_row = next(row for row in result["projections"] if row["age"] == 54)
        self.assertAlmostEqual(retirement_row["closing"], 45300175.15, places=2)
        self.assertAlmostEqual(retirement_row["withdrawal_tax"], 461618.72, places=2)
        self.assertAlmostEqual(retirement_row["withdrawal_after_tax"], 2277958.27, places=2)

    def test_adhoc_expense_inflation(self):
        """Ensures ad-hoc expenses are correctly inflated over time."""
        inputs = PlannerInputs(
            current_age=40, retirement_age=60, life_expectancy=80,
            avg_inflation_rate=0.05,
            adhoc_expenses=[AdHocExpense(age=65, amount=100000)]
        )
        result = calculate_retirement(inputs)
        
        adhoc_row = next(p for p in result["projections"] if p["age"] == 65)
        expected_ad_hoc = 100000 * ((1 + 0.05) ** (65 - 40))
        self.assertAlmostEqual(adhoc_row["ad_hoc"], expected_ad_hoc, places=2)

    def test_mild_crash_scenario(self):
        """Validates that a mild crash reduces returns for the first 2 retirement years."""
        inputs = PlannerInputs(
            retirement_age=60,
            post_retirement_return=0.10,
            stress_scenario=StressScenario.MILD_CRASH
        )
        result = calculate_retirement(inputs)
        
        # First year of retirement (age 60)
        row1 = next(p for p in result["projections"] if p["age"] == 60)
        expected_return1 = (row1["opening"] + row1["contribution"] - row1["withdrawal"] - row1["ad_hoc"]) * -0.10
        self.assertAlmostEqual(row1["return"], expected_return1, places=2)

        # Second year of retirement (age 61)
        row2 = next(p for p in result["projections"] if p["age"] == 61)
        expected_return2 = (row2["opening"] + row2["contribution"] - row2["withdrawal"] - row2["ad_hoc"]) * -0.10
        self.assertAlmostEqual(row2["return"], expected_return2, places=2)

        # Third year should revert to normal post-retirement return
        row3 = next(p for p in result["projections"] if p["age"] == 62)
        expected_return3 = (row3["opening"] + row3["contribution"] - row3["withdrawal"] - row3["ad_hoc"]) * inputs.post_retirement_return
        self.assertAlmostEqual(row3["return"], expected_return3, places=2)

    def test_severe_crash_scenario(self):
        """Validates that a severe crash reduces returns for the first 2 retirement years."""
        inputs = PlannerInputs(
            retirement_age=60,
            post_retirement_return=0.10,
            stress_scenario=StressScenario.SEVERE_CRASH
        )
        result = calculate_retirement(inputs)
        
        row1 = next(p for p in result["projections"] if p["age"] == 60)
        expected_return1 = (row1["opening"] + row1["contribution"] - row1["withdrawal"] - row1["ad_hoc"]) * -0.20
        self.assertAlmostEqual(row1["return"], expected_return1, places=2)

        row2 = next(p for p in result["projections"] if p["age"] == 61)
        expected_return2 = (row2["opening"] + row2["contribution"] - row2["withdrawal"] - row2["ad_hoc"]) * -0.20
        self.assertAlmostEqual(row2["return"], expected_return2, places=2)

    def test_zero_return_scenario(self):
        """Tests projection logic with zero returns, where corpus changes only by cash flow."""
        inputs = PlannerInputs(
            current_age=50, retirement_age=52, life_expectancy=54,
            current_corpus=1000000, annual_contribution=100000,
            current_annual_expenses=50000,
            pre_retirement_return=0.0, post_retirement_return=0.0,
            avg_inflation_rate=0.0, contribution_increase=0.0,
            adhoc_expenses=[]
        )
        result = calculate_retirement(inputs)
        
        # Pre-retirement (age 50, 51)
        p_50 = next(p for p in result["projections"] if p["age"] == 50)
        self.assertEqual(p_50["return"], 0)
        self.assertEqual(p_50["closing"], 1000000 + 100000) # Opening + Contribution

        p_51 = next(p for p in result["projections"] if p["age"] == 51)
        self.assertEqual(p_51["return"], 0)
        self.assertEqual(p_51["closing"], 1100000 + 100000) # Opening + Contribution

        # Post-retirement (age 52, 53, 54)
        p_52 = next(p for p in result["projections"] if p["age"] == 52)
        self.assertEqual(p_52["return"], 0)
        # Gross withdrawal = Net / (1 - tax_rate). Here tax is non-zero.
        self.assertAlmostEqual(p_52["closing"], 1200000 - p_52["withdrawal"], places=2)

    def test_zero_inflation_scenario(self):
        """With zero inflation, annual expenses should remain constant in retirement."""
        inputs = PlannerInputs(
            retirement_age=60, life_expectancy=65,
            current_annual_expenses=100000,
            avg_inflation_rate=0.0
        )
        result = calculate_retirement(inputs)
        
        for age in range(60, 66):
            row = next(p for p in result["projections"] if p["age"] == age)
            self.assertEqual(row["withdrawal_after_tax"], 100000)

    def test_tax_exemption_logic(self):
        """Verifies that the LTCG exemption correctly reduces the tax burden."""
        # Scenario 1: No exemption
        inputs_no_exempt = PlannerInputs(
            retirement_age=60, life_expectancy=61, current_annual_expenses=1000000,
            allocation_equity=1.0, equity_ltcg_split=1.0, tax_ltcg=0.10,
            allocation_debt=0.0, allocation_arbitrage=0.0,
            ltcg_exemption=0.0, adhoc_expenses=[]
        )
        result_no_exempt = calculate_retirement(inputs_no_exempt)
        tax_no_exempt = result_no_exempt["projections"][0]["withdrawal_tax"]
        gross_no_exempt = 1000000 / (1 - 0.10)
        self.assertAlmostEqual(tax_no_exempt, gross_no_exempt - 1000000, places=2)

        # Scenario 2: With exemption
        inputs_with_exempt = inputs_no_exempt.copy(update={"ltcg_exemption": 100000})
        result_with_exempt = calculate_retirement(inputs_with_exempt)
        tax_with_exempt = result_with_exempt["projections"][0]["withdrawal_tax"]

        # Tax should be lower with the exemption
        self.assertLess(tax_with_exempt, tax_no_exempt)
        
        # Verify the math: G = (Net - Exempt*Tax) / (1 - BlendedRate)
        gross_with_exempt = (1000000 - (100000 * 0.10)) / (1 - 0.10)
        self.assertAlmostEqual(result_with_exempt["projections"][0]["withdrawal"], gross_with_exempt, places=2)

    def test_peak_age_and_final_corpus(self):
        """Tests calculation of peak asset age and final corpus."""
        inputs = PlannerInputs(current_age=88, retirement_age=89, life_expectancy=90)
        result = calculate_retirement(inputs)
        metrics = result["metrics"]
        projections = result["projections"]

        # Peak age should be the age with the highest closing corpus
        max_corpus_row = max(projections, key=lambda x: x["closing"])
        self.assertEqual(metrics["peak_age"], max_corpus_row["age"])
        
        # Final corpus should match the closing balance of the last year
        self.assertEqual(metrics["final_corpus"], projections[-1]["closing"])

    # --- Validation Tests ---

    def test_invalid_age_configuration(self):
        """Ensures retirement age is after current age."""
        with self.assertRaises(ValueError):
            PlannerInputs(current_age=60, retirement_age=58)

    def test_invalid_portfolio_allocation(self):
        """Portfolio allocation must sum to 100%."""
        with self.assertRaises(ValueError):
            PlannerInputs(allocation_equity=0.5, allocation_debt=0.5, allocation_arbitrage=0.5)

    def test_invalid_equity_split(self):
        """Equity sub-allocation (LTCG/STCG) must sum to 100%."""
        with self.assertRaises(ValueError):
            PlannerInputs(equity_ltcg_split=0.8, equity_stcg_split=0.3)

    def test_duplicate_adhoc_age(self):
        """Ad-hoc expenses cannot have duplicate ages."""
        with self.assertRaises(ValueError):
            PlannerInputs(adhoc_expenses=[
                AdHocExpense(age=60, amount=1000),
                AdHocExpense(age=60, amount=2000)
            ])

if __name__ == "__main__":
    unittest.main()
