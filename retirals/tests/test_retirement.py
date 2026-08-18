import unittest
from src.models import PlannerInputs, AdHocExpense, StressScenario
from src.retirement_engine import run_projection

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
        result = run_projection(inputs)
        metrics = result["metrics"]

        # Key metric validation
        self.assertAlmostEqual(metrics["corpus_at_retirement"], 42131033.64, places=1)
        self.assertAlmostEqual(metrics["final_corpus"], 893537171.0, places=-2, msg="Final corpus should match workbook.")
        self.assertEqual(metrics["years_in_retirement"], 36)
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
        result = run_projection(inputs)
        
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
        result = run_projection(inputs)
        
        # First year of retirement (age 60)
        row1 = next(p for p in result["projections"] if p["age"] == 60)
        expected_return1 = (row1["opening"] + row1["contribution"] - row1["withdrawal"]) * -0.10
        self.assertAlmostEqual(row1["return"], expected_return1, places=2)

        # Second year of retirement (age 61)
        row2 = next(p for p in result["projections"] if p["age"] == 61)
        expected_return2 = (row2["opening"] + row2["contribution"] - row2["withdrawal"]) * -0.10
        self.assertAlmostEqual(row2["return"], expected_return2, places=2)

        # Third year should revert to normal post-retirement return
        row3 = next(p for p in result["projections"] if p["age"] == 62)
        expected_return3 = (row3["opening"] + row3["contribution"] - row3["withdrawal"]) * inputs.post_retirement_return
        self.assertAlmostEqual(row3["return"], expected_return3, places=2)

    def test_severe_crash_scenario(self):
        """Validates that a severe crash reduces returns for the first 2 retirement years."""
        inputs = PlannerInputs(
            retirement_age=60,
            post_retirement_return=0.10,
            stress_scenario=StressScenario.SEVERE_CRASH
        )
        result = run_projection(inputs)
        
        row1 = next(p for p in result["projections"] if p["age"] == 60)
        expected_return1 = (row1["opening"] + row1["contribution"] - row1["withdrawal"]) * -0.20
        self.assertAlmostEqual(row1["return"], expected_return1, places=2)

        row2 = next(p for p in result["projections"] if p["age"] == 61)
        expected_return2 = (row2["opening"] + row2["contribution"] - row2["withdrawal"]) * -0.20
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
        result = run_projection(inputs)
        
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
        result = run_projection(inputs)
        
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
        result_no_exempt = run_projection(inputs_no_exempt)
        tax_no_exempt = result_no_exempt["projections"][0]["withdrawal_tax"]
        gross_no_exempt = 1000000 / (1 - 0.10)
        self.assertAlmostEqual(tax_no_exempt, gross_no_exempt - 1000000, places=2)

        # Scenario 2: With exemption
        inputs_with_exempt = inputs_no_exempt.copy(update={"ltcg_exemption": 100000})
        result_with_exempt = run_projection(inputs_with_exempt)
        tax_with_exempt = result_with_exempt["projections"][0]["withdrawal_tax"]

        # Tax should be lower with the exemption
        self.assertLess(tax_with_exempt, tax_no_exempt)
        
        # Verify the math: G = (Net - Exempt*Tax) / (1 - BlendedRate)
        gross_with_exempt = (1000000 - (100000 * 0.10)) / (1 - 0.10)
        self.assertAlmostEqual(result_with_exempt["projections"][0]["withdrawal"], gross_with_exempt, places=2)

    def test_tax_exemption_logic_small_withdrawal(self):
        """
        Verifies the LTCG exemption logic for a small withdrawal where the
        LTCG component is *below* the exemption threshold (Case 1).
        """
        inputs = PlannerInputs(
            retirement_age=60, life_expectancy=61,
            current_annual_expenses=100000, # Small withdrawal
            allocation_equity=0.60,
            allocation_debt=0.40,
            allocation_arbitrage=0.0,
            equity_ltcg_split=0.70, # LTCG portion is 42%
            equity_stcg_split=0.30,
            tax_ltcg=0.125,
            tax_stcg=0.20,
            tax_debt=0.20,
            ltcg_exemption=125000,
            adhoc_expenses=[]
        )
        result = run_projection(inputs)
        tax = result["projections"][0]["withdrawal_tax"]
        gross_withdrawal = result["projections"][0]["withdrawal"]
        # In this case, LTCG tax should be zero. Tax is only from STCG and Debt.
        # other_tax_rate = (0.6*0.3*0.2) + (0.4*0.2) = 0.036 + 0.08 = 0.116
        # expected_gross = 100000 / (1 - 0.116) = 113122.17
        expected_tax = (gross_withdrawal * (0.6*0.3*0.2)) + (gross_withdrawal * (0.4*0.2))
        self.assertAlmostEqual(tax, expected_tax, places=2, msg="Tax should only apply to non-LTCG portions")

    def test_peak_age_and_final_corpus(self):
        """Tests calculation of peak asset age and final corpus."""
        inputs = PlannerInputs(current_age=88, retirement_age=89, life_expectancy=90)
        result = run_projection(inputs)
        metrics = result["metrics"]
        projections = result["projections"]

        # Peak age should be the age with the highest closing corpus
        max_corpus_row = max(projections, key=lambda x: x["closing"])
        self.assertEqual(metrics["peak_age"], max_corpus_row["age"])
        
        # Final corpus should match the closing balance of the last year
        self.assertEqual(metrics["final_corpus"], projections[-1]["closing"])

    def test_pension_coverage_metric(self):
        """Validates the new weighted average pension coverage metric."""
        # Scenario: Pension starts mid-retirement and sometimes exceeds expenses.
        inputs = PlannerInputs(
            current_age=58, retirement_age=60, life_expectancy=62,
            current_annual_expenses=100000, avg_inflation_rate=0.0,
            include_pension=True, pension_start_age=61, annual_pension=150000,
            pension_increase=0.0, pension_tax_rate=0.20
        )
        result = run_projection(inputs)
        metrics = result["metrics"]

        # --- Manual Calculation for Validation ---
        # Year 60 (Age): Expense=100k, Pension=0. Covered=0.
        # Year 61 (Age): Expense=100k, Net Pension=150k * (1-0.20) = 120k.
        #                Covered = min(120k, 100k) = 100k.
        # Year 62 (Age): Expense=100k, Net Pension=120k.
        #                Covered = min(120k, 100k) = 100k.
        #
        # Total recurring expense in retirement = 100k + 100k + 100k = 300k
        # Total expense covered by pension = 0 + 100k + 100k = 200k
        #
        # Expected coverage = (200k / 300k) * 100 = 66.67%

        self.assertIn("average_pension_coverage", metrics, "Metric should be in the response.")
        self.assertAlmostEqual(metrics["average_pension_coverage"], 66.67, places=2)

    def test_corpus_exhaustion_logic(self):
        """Tests that the corpus stops at 0 and exhaustion is reported correctly."""
        inputs = PlannerInputs(
            current_age=80, retirement_age=81, life_expectancy=85,
            current_corpus=100000, annual_contribution=0,
            current_annual_expenses=100000, avg_inflation_rate=0.0,
            post_retirement_return=0.10, # Positive return to test it stops
            adhoc_expenses=[]
        )
        result = run_projection(inputs)
        metrics = result["metrics"]
        projections = result["projections"]

        self.assertFalse(metrics["plan_sustainable"])
        self.assertEqual(metrics["corpus_exhaustion_age"], 81)
        
        # Year 81: Opening=100k, Withdrawal > 100k. Closing must be 0.
        row_81 = next(p for p in projections if p["age"] == 81)
        self.assertAlmostEqual(row_81["closing"], 0.0, places=2)

        # Subsequent years must have 0 opening, 0 return, and 0 closing
        row_82 = next(p for p in projections if p["age"] == 82)
        self.assertAlmostEqual(row_82["opening"], 0.0, places=2)
        self.assertAlmostEqual(row_82["return"], 0.0, places=2, msg="No returns on zero corpus.")
        self.assertAlmostEqual(row_82["closing"], 0.0, places=2)

        self.assertAlmostEqual(metrics["final_corpus"], 0.0, places=2)

    def test_plan_is_sustainable_when_corpus_survives(self):
        """Tests a scenario where the plan survives and exhaustion is not reported."""
        inputs = PlannerInputs(
            current_corpus=10000000, # Sufficient corpus
        )
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertTrue(metrics["plan_sustainable"])
        self.assertIsNone(metrics["corpus_exhaustion_age"])
        self.assertGreater(metrics["final_corpus"], 0)

    def test_pension_timing_is_correct(self):
        """Pension should only apply if retired AND after pension start age."""
        inputs = PlannerInputs(
            current_age=50, retirement_age=60, life_expectancy=62,
            current_corpus=100000, annual_contribution=0,
            pre_retirement_return=0.0, post_retirement_return=0.0,
            include_pension=True,
            pension_start_age=55, # Starts BEFORE retirement
            annual_pension=10000, pension_tax_rate=0.0
        )
        result = run_projection(inputs)
        projections = result["projections"]

        # Age 55-59 (pre-retirement): Pension should be zero.
        for age in range(55, 60):
            row = next(p for p in projections if p["age"] == age)
            self.assertEqual(row["pension"], 0, f"Pension should be 0 at pre-retirement age {age}")
            self.assertEqual(row["pension_surplus_reinvested"], 0, f"Pension surplus should be 0 at pre-retirement age {age}")

        # Age 60 (retirement): Pension should now apply.
        row_60 = next(p for p in projections if p["age"] == 60)
        self.assertGreater(row_60["pension"], 0, "Pension should apply at retirement age")

    def test_corpus_exhaustion_accounting_consistency(self):
        """
        Regression test to verify accounting consistency in the exhaustion year.
        This test is EXPECTED TO FAIL until the underlying logic is fixed.
        It asserts that: gross_withdrawal = withdrawal_after_tax + withdrawal_tax.
        """
        inputs = PlannerInputs(
            current_age=80, retirement_age=81, life_expectancy=85,
            current_corpus=100000,
            current_annual_expenses=120000, # Net need is > corpus
            annual_contribution=0,
            avg_inflation_rate=0.0,
            post_retirement_return=0.0,
            # Simplify tax to a flat 20% on all withdrawals
            allocation_equity=0.0,
            allocation_debt=1.0,
            allocation_arbitrage=0.0,
            tax_debt=0.20,
            ltcg_exemption=0.0,
            adhoc_expenses=[]
        )
        result = run_projection(inputs)
        projections = result["projections"]
        metrics = result["metrics"]

        self.assertEqual(metrics["corpus_exhaustion_age"], 81)
        exhaustion_row = next(p for p in projections if p["age"] == 81)

        # 1. Verify the closing corpus is exactly zero.
        self.assertAlmostEqual(exhaustion_row["closing"], 0.0, places=2)

        # 2. Verify the fundamental accounting equation holds true.
        # This assertion is expected to fail with the current logic.
        self.assertAlmostEqual(exhaustion_row["withdrawal"], exhaustion_row["withdrawal_after_tax"] + exhaustion_row["withdrawal_tax"], places=2, msg="Accounting (Gross = Net + Tax) must be consistent in exhaustion year.")

    def test_exhaustion_with_ltcg_exemption(self):
        """
        Verifies that in an exhaustion year with an equity-heavy portfolio,
        the recalculated tax correctly applies the LTCG exemption rules.
        """
        inputs = PlannerInputs(
            current_age=70, retirement_age=71, life_expectancy=75,
            current_corpus=100000, # Available corpus
            current_annual_expenses=150000, # High net need to trigger exhaustion
            annual_contribution=0,
            avg_inflation_rate=0.0,
            post_retirement_return=0.0,
            # Portfolio with significant equity LTCG component
            allocation_equity=0.8,
            allocation_debt=0.2,
            allocation_arbitrage=0.0,
            equity_ltcg_split=0.7, # LTCG is 56% of withdrawal (0.8 * 0.7)
            equity_stcg_split=0.3,
            tax_ltcg=0.10,
            tax_stcg=0.20,
            tax_debt=0.20,
            ltcg_exemption=50000, # Exemption is present
            adhoc_expenses=[]
        )
        result = run_projection(inputs)
        exhaustion_row = next(p for p in result["projections"] if p["age"] == 71)

        # --- Manual Verification ---
        # Gross withdrawal is capped to available corpus: 100,000
        # LTCG portion of withdrawal = 100,000 * (0.8 * 0.7) = 56,000
        # Since 56,000 > 50,000 (exemption), we are in Case 2 of tax logic.
        # Tax = (Gross * FullBlendedRate) - (Exemption * LTCGTax)
        # FullBlendedRate = (0.8*0.7*0.1) + (0.8*0.3*0.2) + (0.2*0.2) = 0.056 + 0.048 + 0.04 = 0.144
        # Expected Tax = (100,000 * 0.144) - (50,000 * 0.10) = 14,400 - 5,000 = 9,400
        # Expected Net = 100,000 - 9,400 = 90,600

        self.assertAlmostEqual(exhaustion_row["withdrawal"], 100000.0, places=2, msg="Gross withdrawal should be capped to available corpus.")
        self.assertAlmostEqual(exhaustion_row["withdrawal_tax"], 9400.0, places=2, msg="Tax in exhaustion year must be recalculated respecting LTCG exemption.")
        self.assertAlmostEqual(exhaustion_row["withdrawal_after_tax"], 90600.0, places=2, msg="Net withdrawal must be recalculated.")
        self.assertAlmostEqual(exhaustion_row["closing"], 0.0, places=2)
        self.assertAlmostEqual(
            exhaustion_row["withdrawal"],
            exhaustion_row["withdrawal_after_tax"] + exhaustion_row["withdrawal_tax"],
            places=2, msg="Accounting must be consistent in LTCG exhaustion year."
        )

    def test_accounting_in_normal_non_exhaustion_year(self):
        """
        Verifies that the accounting equation (Gross = Net + Tax) holds true
        for a normal year where the portfolio is not exhausted. This ensures
        the exhaustion fix does not impact standard calculations.
        """
        inputs = PlannerInputs(
            current_age=60, retirement_age=61, life_expectancy=65,
            current_corpus=5000000, # Ample corpus
            current_annual_expenses=100000,
            annual_contribution=0,
            avg_inflation_rate=0.0,
            post_retirement_return=0.0,
            allocation_equity=0.5,
            allocation_debt=0.5,
            tax_ltcg=0.10,
            tax_debt=0.20,
            ltcg_exemption=100000,
            adhoc_expenses=[]
        )
        result = run_projection(inputs)
        metrics = result["metrics"]
        normal_year_row = next(p for p in result["projections"] if p["age"] == 61)

        # Verify plan does not exhaust
        self.assertTrue(metrics["plan_sustainable"])
        self.assertIsNone(metrics["corpus_exhaustion_age"])

        # Verify accounting is correct
        self.assertGreater(normal_year_row["withdrawal"], 0)
        self.assertAlmostEqual(
            normal_year_row["withdrawal"],
            normal_year_row["withdrawal_after_tax"] + normal_year_row["withdrawal_tax"],
            places=2, msg="Accounting must be consistent in a normal, non-exhaustion year."
        )
        self.assertGreater(normal_year_row["closing"], 0, "Corpus should not be zero in a normal year.")

    def test_post_exhaustion_with_unfunded_expenses(self):
        """
        Tests that after corpus exhaustion, `unfunded_expense` correctly reports
        the shortfall not covered by an insufficient pension.
        """
        inputs = PlannerInputs(
            current_age=70, retirement_age=71, life_expectancy=75,
            current_corpus=100000,
            current_annual_expenses=150000, # High expenses
            avg_inflation_rate=0.0,
            post_retirement_return=0.0,
            include_pension=True,
            pension_start_age=71,
            annual_pension=50000, # Pension is insufficient
            pension_tax_rate=0.20, # Net pension = 40,000
            adhoc_expenses=[]
        )
        result = run_projection(inputs)
        metrics = result["metrics"]
        projections = result["projections"]

        self.assertEqual(metrics["corpus_exhaustion_age"], 71, "Corpus should exhaust at age 71.")

        # Year after exhaustion (age 72)
        post_exhaustion_row = next(p for p in projections if p["age"] == 72)

        self.assertEqual(post_exhaustion_row["opening"], 0)
        self.assertEqual(post_exhaustion_row["withdrawal"], 0)
        self.assertEqual(post_exhaustion_row["return"], 0)
        self.assertEqual(post_exhaustion_row["closing"], 0)
        self.assertGreater(post_exhaustion_row["pension"], 0, "Pension should continue after exhaustion.")

        # Expected unfunded = expense - net_pension = 150,000 - 40,000 = 110,000
        self.assertEqual(post_exhaustion_row["unfunded_expense"], 110000)

    def test_post_exhaustion_with_sufficient_pension(self):
        """
        Tests that after corpus exhaustion, `unfunded_expense` is zero when
        pension is sufficient to cover all recurring expenses.
        """
        inputs = PlannerInputs(
            current_age=70, retirement_age=71, life_expectancy=75,
            current_corpus=100000,
            current_annual_expenses=150000,
            avg_inflation_rate=0.0,
            post_retirement_return=0.0,
            include_pension=True,
            pension_start_age=71,
            annual_pension=200000, # Pension is sufficient
            pension_tax_rate=0.20, # Net pension = 160,000
            adhoc_expenses=[]
        )
        result = run_projection(inputs)
        projections = result["projections"]

        # Year after exhaustion (age 72)
        post_exhaustion_row = next(p for p in projections if p["age"] == 72)

        self.assertEqual(post_exhaustion_row["opening"], 0)
        self.assertEqual(post_exhaustion_row["withdrawal"], 0)
        self.assertEqual(post_exhaustion_row["unfunded_expense"], 0, "Unfunded expense should be 0 when pension is sufficient.")
        self.assertGreater(post_exhaustion_row["pension_surplus_reinvested"], 0, "Pension surplus should be calculated.")

    def test_unfunded_expense_is_zero_before_exhaustion(self):
        """
        Verifies that the `unfunded_expense` field is always zero in years
        before the portfolio is exhausted.
        """
        inputs = PlannerInputs(current_corpus=50000000) # A plan that won't exhaust
        result = run_projection(inputs)
        projections = result["projections"]

        for row in projections:
            self.assertEqual(row["unfunded_expense"], 0, f"Unfunded expense should be 0 at age {row['age']} for a sustainable plan.")


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
