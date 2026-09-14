import unittest
from src.retirement_engine import run_projection, run_monte_carlo, _generate_recommendations, get_return_rate
from src.models import PlannerInputs, StressScenario, ReturnDistribution, AdHocExpense, OneTimeIncome


class TestDeterministicProjections(unittest.TestCase):
    def setUp(self):
        self.base_inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=600000,
            avg_inflation_rate=0.06,
            current_corpus=2000000,
            annual_contribution=500000,
            pre_retirement_return=0.10,
            post_retirement_return=0.08,
            contribution_increase=0.01,
            allocation_equity=0.60,
            allocation_debt=0.30,
            allocation_arbitrage=0.10,
            equity_ltcg_split=0.70,
            equity_stcg_split=0.30,
            tax_ltcg=0.125,
            tax_stcg=0.20,
            tax_debt=0.20,
            tax_arbitrage=0.20,
            ltcg_exemption=125000,
        )

    def test_base_case_young_professional(self):
        result = run_projection(self.base_inputs)
        metrics = result["metrics"]
        self.assertIn("readiness_percent", metrics)
        self.assertIn("corpus_at_retirement", metrics)
        self.assertIn("gap_at_retirement", metrics)
        self.assertIn("plan_sustainable", metrics)
        self.assertGreaterEqual(metrics["corpus_at_retirement"], 0)

    def test_near_retirement(self):
        inputs = self.base_inputs.model_copy(update={
            "current_age": 55,
            "retirement_age": 60,
            "current_corpus": 5000000,
            "annual_contribution": 100000,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertGreaterEqual(metrics["years_in_retirement"], 0)
        self.assertIn("corpus_at_retirement", metrics)

    def test_with_pension(self):
        inputs = self.base_inputs.model_copy(update={
            "include_pension": True,
            "pension_start_age": 60,
            "annual_pension": 600000,
            "pension_increase": 0.05,
            "pension_tax_rate": 0.20,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertGreater(metrics["total_pension_received"], 0)
        self.assertGreater(metrics["average_pension_coverage"], 0)

    def test_with_adhoc_expenses(self):
        inputs = self.base_inputs.model_copy(update={
            "adhoc_expenses": [
                AdHocExpense(age=45, amount=1000000),
                AdHocExpense(age=70, amount=2000000),
            ]
        })
        result = run_projection(inputs)
        projections = result["projections"]
        adhoc_years = [p for p in projections if p["ad_hoc"] > 0]
        self.assertEqual(len(adhoc_years), 2)

    def test_conservative_portfolio(self):
        inputs = self.base_inputs.model_copy(update={
            "allocation_equity": 0.30,
            "allocation_debt": 0.60,
            "allocation_arbitrage": 0.10,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertIn("readiness_percent", metrics)

    def test_aggressive_portfolio(self):
        inputs = self.base_inputs.model_copy(update={
            "allocation_equity": 0.80,
            "allocation_debt": 0.15,
            "allocation_arbitrage": 0.05,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertIn("readiness_percent", metrics)

    def test_stress_scenario_mild_crash(self):
        inputs = self.base_inputs.model_copy(update={
            "stress_scenario": StressScenario.MILD_CRASH,
        })
        for age in [60, 61]:
            rate = get_return_rate(age, inputs)
            self.assertEqual(rate, -0.10)

    def test_stress_scenario_severe_crash(self):
        inputs = self.base_inputs.model_copy(update={
            "stress_scenario": StressScenario.SEVERE_CRASH,
        })
        for age in [60, 61]:
            rate = get_return_rate(age, inputs)
            self.assertEqual(rate, -0.20)

    def test_zero_inflation(self):
        inputs = self.base_inputs.model_copy(update={
            "avg_inflation_rate": 0.0,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertIn("readiness_percent", metrics)

    def test_lump_sum_at_retirement(self):
        inputs = self.base_inputs.model_copy(update={
            "one_time_lumpsum": 1000000,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        projections = result["projections"]
        lumpsum_rows = [p for p in projections if p["lumpsum"] > 0]
        self.assertEqual(len(lumpsum_rows), 1)
        self.assertEqual(lumpsum_rows[0]["lumpsum"], 1000000)

    def test_early_retirement(self):
        inputs = self.base_inputs.model_copy(update={
            "retirement_age": 50,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertEqual(metrics["years_in_retirement"], inputs.life_expectancy - inputs.retirement_age)

    def test_late_retirement(self):
        inputs = self.base_inputs.model_copy(update={
            "retirement_age": 65,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertEqual(metrics["years_in_retirement"], inputs.life_expectancy - inputs.retirement_age)


class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        self.base_inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=600000,
            avg_inflation_rate=0.06,
            current_corpus=2000000,
            annual_contribution=500000,
            pre_retirement_return=0.10,
            post_retirement_return=0.08,
            contribution_increase=0.01,
            allocation_equity=0.60,
            allocation_debt=0.30,
            allocation_arbitrage=0.10,
            equity_ltcg_split=0.70,
            equity_stcg_split=0.30,
            tax_ltcg=0.125,
            tax_stcg=0.20,
            tax_debt=0.20,
            tax_arbitrage=0.20,
            ltcg_exemption=125000,
        )

    def test_minimum_ages(self):
        inputs = PlannerInputs(
            current_age=18,
            retirement_age=19,
            life_expectancy=19,
            current_annual_expenses=100000,
            current_corpus=1000,
            annual_contribution=1000,
            adhoc_expenses=[],
        )
        result = run_projection(inputs)
        self.assertIsNotNone(result)

    def test_maximum_ages(self):
        inputs = PlannerInputs(
            current_age=100,
            retirement_age=101,
            life_expectancy=101,
            current_annual_expenses=100000,
            current_corpus=1000,
            annual_contribution=1000,
            adhoc_expenses=[],
        )
        result = run_projection(inputs)
        self.assertIsNotNone(result)

    def test_zero_corpus(self):
        inputs = self.base_inputs.model_copy(update={
            "current_corpus": 0,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertGreater(metrics["corpus_at_retirement"], 0)

    def test_zero_contributions(self):
        inputs = self.base_inputs.model_copy(update={
            "annual_contribution": 0,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertGreaterEqual(metrics["corpus_at_retirement"], 2000000)

    def test_negative_returns(self):
        inputs = self.base_inputs.model_copy(update={
            "pre_retirement_return": -0.05,
            "post_retirement_return": -0.05,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertIn("readiness_percent", metrics)

    def test_zero_allocation_one_class(self):
        inputs = self.base_inputs.model_copy(update={
            "allocation_equity": 0.0,
            "allocation_debt": 1.0,
            "allocation_arbitrage": 0.0,
        })
        result = run_projection(inputs)
        self.assertIsNotNone(result)

    def test_100_percent_tax_rate(self):
        inputs = self.base_inputs.model_copy(update={
            "tax_ltcg": 1.0,
            "tax_stcg": 1.0,
            "tax_debt": 1.0,
            "tax_arbitrage": 1.0,
        })
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertIn("readiness_percent", metrics)


class TestMonteCarlo(unittest.TestCase):
    def setUp(self):
        self.base_inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=600000,
            avg_inflation_rate=0.06,
            current_corpus=2000000,
            annual_contribution=500000,
            pre_retirement_return=0.10,
            post_retirement_return=0.08,
            contribution_increase=0.01,
            allocation_equity=0.60,
            allocation_debt=0.30,
            allocation_arbitrage=0.10,
            equity_ltcg_split=0.70,
            equity_stcg_split=0.30,
            tax_ltcg=0.125,
            tax_stcg=0.20,
            tax_debt=0.20,
            tax_arbitrage=0.20,
            ltcg_exemption=125000,
            num_simulations=100,
            monte_carlo_seed=42,
        )

    def test_basic_run(self):
        result = run_monte_carlo(self.base_inputs)
        metrics = result["metrics"]
        self.assertIn("success_rate", metrics)
        self.assertIn("median_final_corpus", metrics)
        self.assertGreaterEqual(metrics["success_rate"], 0)
        self.assertLessEqual(metrics["success_rate"], 100)

    def test_with_correlations(self):
        inputs = self.base_inputs.model_copy(update={
            "equity_debt_correlation": 0.5,
            "equity_arbitrage_correlation": 0.3,
            "debt_arbitrage_correlation": -0.2,
        })
        result = run_monte_carlo(inputs)
        metrics = result["metrics"]
        self.assertIn("success_rate", metrics)

    def test_sensitivity_analysis(self):
        inputs = self.base_inputs.model_copy(update={
            "retirement_age_sensitivity": [58, 60, 62],
        })
        result = run_monte_carlo(inputs)
        sensitivity = result.get("retirement_age_sensitivity", {})
        self.assertIn("58", sensitivity)
        self.assertIn("60", sensitivity)
        self.assertIn("62", sensitivity)

    def test_lognormal_distribution(self):
        inputs = self.base_inputs.model_copy(update={
            "return_distribution": ReturnDistribution.LOGNORMAL,
        })
        result = run_monte_carlo(inputs)
        self.assertIsNotNone(result)

    def test_normal_distribution(self):
        inputs = self.base_inputs.model_copy(update={
            "return_distribution": ReturnDistribution.NORMAL,
        })
        result = run_monte_carlo(inputs)
        self.assertIsNotNone(result)

    def test_minimum_simulations(self):
        inputs = self.base_inputs.model_copy(update={
            "num_simulations": 100,
        })
        result = run_monte_carlo(inputs)
        self.assertEqual(result["num_simulations"], 100)

    def test_maximum_simulations(self):
        inputs = self.base_inputs.model_copy(update={
            "num_simulations": 50000,
        })
        result = run_monte_carlo(inputs)
        self.assertEqual(result["num_simulations"], 50000)

    def test_extreme_correlations(self):
        inputs = self.base_inputs.model_copy(update={
            "equity_debt_correlation": 0.99,
            "equity_arbitrage_correlation": -0.99,
            "debt_arbitrage_correlation": 0.99,
        })
        result = run_monte_carlo(inputs)
        self.assertIsNotNone(result)

    def test_high_volatility(self):
        inputs = self.base_inputs.model_copy(update={
            "volatility_equity": 0.50,
            "volatility_debt": 0.30,
            "volatility_arbitrage": 0.40,
        })
        result = run_monte_carlo(inputs)
        metrics = result["metrics"]
        self.assertIn("success_rate", metrics)


class TestRecommendations(unittest.TestCase):
    def setUp(self):
        self.base_inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=600000,
            avg_inflation_rate=0.06,
            current_corpus=2000000,
            annual_contribution=500000,
            pre_retirement_return=0.10,
            post_retirement_return=0.08,
            contribution_increase=0.01,
            allocation_equity=0.60,
            allocation_debt=0.30,
            allocation_arbitrage=0.10,
            equity_ltcg_split=0.70,
            equity_stcg_split=0.30,
            tax_ltcg=0.125,
            tax_stcg=0.20,
            tax_debt=0.20,
            tax_arbitrage=0.20,
            ltcg_exemption=125000,
        )

    def test_healthy_plan(self):
        inputs = self.base_inputs.model_copy(update={
            "current_corpus": 50000000,
            "annual_contribution": 2000000,
        })
        proj = run_projection(inputs)
        mc = run_monte_carlo(inputs.model_copy(update={"num_simulations": 100, "monte_carlo_seed": 42}))
        mc_summary = {
            "success_rate": mc["metrics"]["success_rate"],
            "readiness_percent": proj["metrics"]["readiness_percent"],
            "gap_at_retirement": proj["metrics"]["gap_at_retirement"],
            "minimum_corpus_required": proj["metrics"]["minimum_corpus_required"],
            "target_annual_contribution_for_gap": proj["metrics"]["target_annual_contribution_for_gap"],
            "required_pre_retirement_return": proj["metrics"]["required_pre_retirement_return"],
            "required_post_retirement_return": proj["metrics"]["required_post_retirement_return"],
            "failure_age_percentiles": mc.get("failure_age_percentiles", {}),
        }
        recs = _generate_recommendations(inputs, mc_summary)
        self.assertTrue(any("plan looks healthy" in r.lower() for r in recs))

    def test_fragile_plan(self):
        inputs = self.base_inputs.model_copy(update={
            "current_corpus": 3000000,
            "annual_contribution": 200000,
        })
        proj = run_projection(inputs)
        mc = run_monte_carlo(inputs.model_copy(update={"num_simulations": 100, "monte_carlo_seed": 42}))
        mc_summary = {
            "success_rate": mc["metrics"]["success_rate"],
            "readiness_percent": proj["metrics"]["readiness_percent"],
            "gap_at_retirement": proj["metrics"]["gap_at_retirement"],
            "minimum_corpus_required": proj["metrics"]["minimum_corpus_required"],
            "target_annual_contribution_for_gap": proj["metrics"]["target_annual_contribution_for_gap"],
            "required_pre_retirement_return": proj["metrics"]["required_pre_retirement_return"],
            "required_post_retirement_return": proj["metrics"]["required_post_retirement_return"],
            "failure_age_percentiles": mc.get("failure_age_percentiles", {}),
        }
        recs = _generate_recommendations(inputs, mc_summary)
        self.assertTrue(any("fragile" in r.lower() for r in recs))

    def test_high_risk_plan(self):
        inputs = self.base_inputs.model_copy(update={
            "current_corpus": 500000,
            "annual_contribution": 50000,
        })
        proj = run_projection(inputs)
        mc = run_monte_carlo(inputs.model_copy(update={"num_simulations": 100, "monte_carlo_seed": 42}))
        mc_summary = {
            "success_rate": mc["metrics"]["success_rate"],
            "readiness_percent": proj["metrics"]["readiness_percent"],
            "gap_at_retirement": proj["metrics"]["gap_at_retirement"],
            "minimum_corpus_required": proj["metrics"]["minimum_corpus_required"],
            "target_annual_contribution_for_gap": proj["metrics"]["target_annual_contribution_for_gap"],
            "required_pre_retirement_return": proj["metrics"]["required_pre_retirement_return"],
            "required_post_retirement_return": proj["metrics"]["required_post_retirement_return"],
            "failure_age_percentiles": mc.get("failure_age_percentiles", {}),
        }
        recs = _generate_recommendations(inputs, mc_summary)
        self.assertTrue(any("high risk" in r.lower() for r in recs))

    def test_one_time_income_changes_mc_outcome(self):
        baseline = run_monte_carlo(self.base_inputs.model_copy(update={
            "num_simulations": 100,
            "monte_carlo_seed": 42,
        }))
        with_income = run_monte_carlo(self.base_inputs.model_copy(update={
            "num_simulations": 100,
            "monte_carlo_seed": 42,
            "one_time_incomes": [OneTimeIncome(age=70, amount=10000000)],
        }))
        self.assertGreaterEqual(
            with_income["metrics"]["success_rate"],
            baseline["metrics"]["success_rate"],
        )
        self.assertGreater(
            with_income["metrics"]["median_final_corpus"],
            baseline["metrics"]["median_final_corpus"],
        )


class TestBoundaryValidations(unittest.TestCase):
    def test_retirement_age_greater_than_current(self):
        with self.assertRaises(ValueError):
            PlannerInputs(current_age=60, retirement_age=60)

    def test_life_expectancy_greater_than_retirement(self):
        with self.assertRaises(ValueError):
            PlannerInputs(life_expectancy=50, retirement_age=60)

    def test_allocation_sums_to_one(self):
        with self.assertRaises(ValueError):
            PlannerInputs(allocation_equity=0.8, allocation_debt=0.3, allocation_arbitrage=0.1)

    def test_equity_split_sums_to_one(self):
        with self.assertRaises(ValueError):
            PlannerInputs(equity_ltcg_split=0.5, equity_stcg_split=0.6)

    def test_adhoc_age_in_valid_range(self):
        with self.assertRaises(ValueError):
            PlannerInputs(
                current_age=30,
                adhoc_expenses=[AdHocExpense(age=20, amount=100000)]
            )

    def test_pension_start_age_valid(self):
        with self.assertRaises(ValueError):
            PlannerInputs(
                include_pension=True,
                pension_start_age=20,
                current_age=30
            )


class TestTaxCalculations(unittest.TestCase):
    def test_ltcg_exemption_impact(self):
        inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=500000,
            ltcg_exemption=0,
            allocation_equity=1.0,
            allocation_debt=0.0,
            allocation_arbitrage=0.0,
            equity_ltcg_split=1.0,
            equity_stcg_split=0.0,
            tax_ltcg=0.125,
        )
        result = run_projection(inputs)
        projections = result["projections"]
        retired_years = [p for p in projections if p["age"] >= 60 and p["withdrawal"] > 0]
        self.assertGreater(len(retired_years), 0)

    def test_blended_tax_rates(self):
        inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=500000,
            allocation_equity=0.50,
            equity_ltcg_split=0.70,
            equity_stcg_split=0.30,
            allocation_debt=0.30,
            allocation_arbitrage=0.20,
            tax_ltcg=0.10,
            tax_stcg=0.15,
            tax_debt=0.20,
            tax_arbitrage=0.20,
        )
        result = run_projection(inputs)
        projections = result["projections"]
        retired_years = [p for p in projections if p["age"] >= 60 and p["withdrawal"] > 0]
        self.assertGreater(len(retired_years), 0)

    def test_withdrawal_sequencing(self):
        inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=1000000,
            current_corpus=10000000,
            allocation_equity=0.60,
            equity_ltcg_split=0.70,
            equity_stcg_split=0.30,
            tax_ltcg=0.10,
            tax_stcg=0.20,
            tax_debt=0.20,
            tax_arbitrage=0.20,
        )
        result = run_projection(inputs)
        self.assertIsNotNone(result)


class TestGapAnalysis(unittest.TestCase):
    def test_gap_calculation(self):
        inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=600000,
            current_corpus=1000000,
            annual_contribution=100000,
        )
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertIn("gap_at_retirement", metrics)
        self.assertIn("readiness_percent", metrics)
        if metrics["gap_at_retirement"] > 0:
            self.assertLess(metrics["readiness_percent"], 100)

    def test_target_contribution_calculation(self):
        inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=600000,
            current_corpus=1000000,
            annual_contribution=100000,
        )
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertIn("target_annual_contribution_for_gap", metrics)

    def test_required_return_calculations(self):
        inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=600000,
            current_corpus=1000000,
            annual_contribution=100000,
        )
        result = run_projection(inputs)
        metrics = result["metrics"]
        self.assertIn("required_pre_retirement_return", metrics)
        self.assertIn("required_post_retirement_return", metrics)


class TestOneTimeIncomes(unittest.TestCase):
    """Regression tests for the Future One-Time Incomes feature."""

    def setUp(self):
        self.base_inputs = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=600000,
            avg_inflation_rate=0.06,
            current_corpus=2000000,
            annual_contribution=500000,
            pre_retirement_return=0.10,
            post_retirement_return=0.08,
            contribution_increase=0.01,
            allocation_equity=0.60,
            allocation_debt=0.30,
            allocation_arbitrage=0.10,
            equity_ltcg_split=0.70,
            equity_stcg_split=0.30,
            tax_ltcg=0.125,
            tax_stcg=0.20,
            tax_debt=0.20,
            tax_arbitrage=0.20,
            ltcg_exemption=125000,
            adhoc_expenses=[],
            one_time_incomes=[],
        )

    def test_no_incomes_projection_unchanged(self):
        """No incomes -> existing projection behavior remains unchanged."""
        baseline = run_projection(self.base_inputs)
        explicit_empty = run_projection(self.base_inputs.model_copy(update={"one_time_incomes": []}))
        self.assertEqual(baseline["metrics"], explicit_empty["metrics"])
        self.assertEqual(baseline["projections"], explicit_empty["projections"])
        for row in baseline["projections"]:
            self.assertEqual(row["one_time_income"], 0)

    def test_one_income_increases_corpus(self):
        """A single one-time income must increase the projected corpus."""
        without = run_projection(self.base_inputs)
        with_income = run_projection(self.base_inputs.model_copy(update={
            "one_time_incomes": [OneTimeIncome(age=40, amount=1000000)],
        }))
        self.assertGreater(
            with_income["metrics"]["final_corpus"],
            without["metrics"]["final_corpus"],
        )
        income_rows = [p for p in with_income["projections"] if p["one_time_income"] > 0]
        self.assertEqual(len(income_rows), 1)
        self.assertEqual(income_rows[0]["age"], 40)
        self.assertAlmostEqual(income_rows[0]["one_time_income"], 1000000 * ((1 + 0.06) ** 10), places=2)

    def test_income_inflated_from_todays_money(self):
        """Income defined in today's money must be inflated to the event age."""
        inputs = self.base_inputs.model_copy(update={
            "avg_inflation_rate": 0.05,
            "one_time_incomes": [OneTimeIncome(age=65, amount=100000)],
        })
        result = run_projection(inputs)
        income_row = next(p for p in result["projections"] if p["age"] == 65)
        expected = 100000 * ((1 + 0.05) ** (65 - 30))
        self.assertAlmostEqual(income_row["one_time_income"], expected, places=2)

    def test_income_prevents_premature_exhaustion(self):
        """A one-time income must be available before the corpus-exhaustion check.

        Opening corpus 5L, income 20L and withdrawal 15L in the same year:
        the corpus must NOT be marked exhausted merely because the opening
        corpus was 5L.
        """
        # Deterministic scenario: zero returns, zero taxes, zero inflation.
        base = PlannerInputs(
            current_age=59,
            retirement_age=60,
            life_expectancy=65,
            current_annual_expenses=1500000,
            avg_inflation_rate=0.0,
            current_corpus=500000,
            annual_contribution=0,
            allocation_equity=1.0,
            allocation_debt=0.0,
            allocation_arbitrage=0.0,
            return_equity=0.0,
            equity_ltcg_split=1.0,
            equity_stcg_split=0.0,
            tax_ltcg=0.0,
            tax_stcg=0.0,
            tax_debt=0.0,
            tax_arbitrage=0.0,
            ltcg_exemption=0,
            adhoc_expenses=[],
            one_time_incomes=[],
        )
        without = run_projection(base)
        self.assertEqual(without["metrics"]["corpus_exhaustion_age"], 60)

        with_income = run_projection(base.model_copy(update={
            "one_time_incomes": [OneTimeIncome(age=60, amount=2000000)],
        }))
        # The income must prevent exhaustion at age 60; the corpus now lasts
        # until age 61 instead.
        self.assertEqual(with_income["metrics"]["corpus_exhaustion_age"], 61)
        row_60 = next(p for p in with_income["projections"] if p["age"] == 60)
        self.assertEqual(row_60["one_time_income"], 2000000)
        self.assertEqual(row_60["unfunded_expense"], 0)
        self.assertEqual(row_60["withdrawal"], 1500000)
        self.assertEqual(row_60["closing"], 1000000)

    def test_invalid_income_age_rejected(self):
        """Income age outside [current_age, life_expectancy] is rejected."""
        with self.assertRaises(ValueError):
            PlannerInputs(
                current_age=30,
                retirement_age=60,
                life_expectancy=85,
                adhoc_expenses=[],
                one_time_incomes=[OneTimeIncome(age=20, amount=100000)],
            )
        with self.assertRaises(ValueError):
            PlannerInputs(
                current_age=30,
                retirement_age=60,
                life_expectancy=85,
                adhoc_expenses=[],
                one_time_incomes=[OneTimeIncome(age=90, amount=100000)],
            )

    def test_duplicate_income_age_rejected(self):
        """Duplicate income ages within the income list are rejected."""
        with self.assertRaises(ValueError):
            PlannerInputs(
                current_age=30,
                retirement_age=60,
                life_expectancy=85,
                adhoc_expenses=[],
                one_time_incomes=[
                    OneTimeIncome(age=50, amount=100000),
                    OneTimeIncome(age=50, amount=200000),
                ],
            )

    def test_export_import_preserves_incomes(self):
        """Export/import (mirroring validate_export.py) preserves income events."""
        inputs = self.base_inputs.model_copy(update={
            "one_time_incomes": [
                OneTimeIncome(age=45, amount=1500000, inflation_rate=0.04),
                OneTimeIncome(age=72, amount=800000),
            ],
        })
        # Mirror the reconstruction logic in validate_export.py: the export
        # carries plain dicts which are converted back to model instances.
        inputs_dict = inputs.model_dump()
        one_time_incomes = inputs_dict.get("one_time_incomes", [])
        if one_time_incomes:
            inputs_dict["one_time_incomes"] = [OneTimeIncome(**item) for item in one_time_incomes]
        reconstructed = PlannerInputs(**inputs_dict)

        self.assertEqual(len(reconstructed.one_time_incomes), 2)
        self.assertEqual(reconstructed.one_time_incomes[0].age, 45)
        self.assertEqual(reconstructed.one_time_incomes[0].amount, 1500000)
        self.assertEqual(reconstructed.one_time_incomes[0].inflation_rate, 0.04)
        self.assertEqual(reconstructed.one_time_incomes[1].age, 72)
        self.assertEqual(reconstructed.one_time_incomes[1].amount, 800000)
        self.assertIsNone(reconstructed.one_time_incomes[1].inflation_rate)

        # The reconstructed plan must produce identical projections.
        self.assertEqual(
            run_projection(reconstructed)["projections"],
            run_projection(inputs)["projections"],
        )

    def test_income_custom_inflation_overrides_general(self):
        """Custom income inflation rate overrides the general inflation rate."""
        inputs = self.base_inputs.model_copy(update={
            "avg_inflation_rate": 0.05,  # General inflation
            "one_time_incomes": [
                # This one should use its own 8% inflation rate
                OneTimeIncome(age=65, amount=100000, inflation_rate=0.08),
                # This one should fall back to the general 5% inflation rate
                OneTimeIncome(age=70, amount=50000),
            ],
        })
        result = run_projection(inputs)
        custom_row = next(p for p in result["projections"] if p["age"] == 65)
        expected_custom = 100000 * ((1 + 0.08) ** (65 - 30))
        self.assertAlmostEqual(custom_row["one_time_income"], expected_custom, places=2)
        self.assertNotAlmostEqual(
            custom_row["one_time_income"], 100000 * ((1 + 0.05) ** (65 - 30)),
            places=2, msg="Should not use general inflation rate.",
        )
        general_row = next(p for p in result["projections"] if p["age"] == 70)
        expected_general = 50000 * ((1 + 0.05) ** (70 - 30))
        self.assertAlmostEqual(general_row["one_time_income"], expected_general, places=2)

    def test_multiple_incomes_each_occur_exactly_once(self):
        """Multiple incomes at different ages each occur exactly once."""
        inputs = self.base_inputs.model_copy(update={
            "one_time_incomes": [
                OneTimeIncome(age=40, amount=500000),
                OneTimeIncome(age=70, amount=750000),
            ],
        })
        result = run_projection(inputs)
        income_rows = [p for p in result["projections"] if p["one_time_income"] > 0]
        self.assertEqual(len(income_rows), 2)
        self.assertEqual(sorted(row["age"] for row in income_rows), [40, 70])
        row_40 = next(p for p in result["projections"] if p["age"] == 40)
        row_70 = next(p for p in result["projections"] if p["age"] == 70)
        self.assertAlmostEqual(row_40["one_time_income"], 500000 * ((1 + 0.06) ** 10), places=2)
        self.assertAlmostEqual(row_70["one_time_income"], 750000 * ((1 + 0.06) ** 40), places=2)

    def test_income_and_expense_same_age_both_apply(self):
        """An income and an expense at the same age are both allowed and both apply."""
        inputs = self.base_inputs.model_copy(update={
            "adhoc_expenses": [AdHocExpense(age=70, amount=1000000)],
            "one_time_incomes": [OneTimeIncome(age=70, amount=2000000)],
        })
        result = run_projection(inputs)
        row = next(p for p in result["projections"] if p["age"] == 70)
        self.assertAlmostEqual(row["ad_hoc"], 1000000 * ((1 + 0.06) ** 40), places=2)
        self.assertAlmostEqual(row["one_time_income"], 2000000 * ((1 + 0.06) ** 40), places=2)

    def test_income_at_retirement_age(self):
        """An income at the retirement age applies correctly in that year."""
        without = run_projection(self.base_inputs)
        with_income = run_projection(self.base_inputs.model_copy(update={
            "one_time_incomes": [OneTimeIncome(age=60, amount=1000000)],
        }))
        row = next(p for p in with_income["projections"] if p["age"] == 60)
        self.assertAlmostEqual(row["one_time_income"], 1000000 * ((1 + 0.06) ** 30), places=2)
        closing_without = next(p for p in without["projections"] if p["age"] == 60)["closing"]
        self.assertGreater(row["closing"], closing_without)

    def test_future_income_after_exhaustion_funds_year(self):
        """If the corpus reaches zero before a future one-time income, the income
        must still fund that year's expense and contribute to the closing corpus.

        This is the regression for the bug where a one-time income at an age
        after corpus exhaustion was calculated but not available to fund the
        year's cash flow.
        """
        pre_retirement_return = 0.0
        post_retirement_return = 0.0

        def little_scenario(*, life_expectancy, one_time_incomes):
            return PlannerInputs(
                current_age=45,
                retirement_age=50,
                life_expectancy=life_expectancy,
                current_annual_expenses=1000000,
                avg_inflation_rate=0.0,
                current_corpus=500000,
                annual_contribution=0,
                pre_retirement_return=pre_retirement_return,
                post_retirement_return=post_retirement_return,
                allocation_equity=1.0,
                allocation_debt=0.0,
                allocation_arbitrage=0.0,
                equity_ltcg_split=1.0,
                equity_stcg_split=0.0,
                debt_portion_for_tax=0.0,
                arbitrage_portion_for_tax=0.0,
                tax_ltcg=0.0,
                tax_stcg=0.0,
                tax_debt=0.0,
                tax_arbitrage=0.0,
                ltcg_exemption=0,
                reinvest_pension_surplus=False,
                adhoc_expenses=[],
                one_time_incomes=one_time_incomes,
            )

        # Baseline: corpus is exhausted before the income age, so the income
        # should have no portfolio to fund and the shortfall continues.
        baseline = run_projection(little_scenario(life_expectancy=60, one_time_incomes=[]))
        post_exhaustion_rows = [p for p in baseline["projections"] if p["age"] >= 51]
        self.assertTrue(post_exhaustion_rows)
        for row in post_exhaustion_rows:
            self.assertEqual(row["one_time_income"], 0.0)
            self.assertEqual(row["closing"], 0.0)
        baseline_exhaustion_age = baseline["metrics"]["corpus_exhaustion_age"]

        # With the future income, the income still occurs at its age and because
        # it is a beginning-of-year inflow it must make available funds before
        # the year's withdrawal is assessed.
        # Use a long enough horizon that the corpus does not run out again for
        # at least the six years following the income year, so we can assert
        # the income genuinely reseeds the portfolio.
        with_income = run_projection(
            little_scenario(
                life_expectancy=66,
                one_time_incomes=[OneTimeIncome(age=55, amount=5000000)],
            )
        )

        income_row = next(p for p in with_income["projections"] if p["age"] == 55)
        self.assertEqual(income_row["one_time_income"], 5000000.0)
        # The income must be large enough to fund that year's withdrawal, so
        # there should be no unfunded expense in the income year.
        self.assertEqual(income_row["unfunded_expense"], 0.0)
        # Because the income was larger than the withdrawal, closing corpus
        # in the income year should be the leftover after the withdrawal.
        self.assertGreater(income_row["closing"], 0.0)

        # After the income year, the corpus should no longer be exhausted until
        # it would have done so anyway given the post-income drawdowns.
        after_income_rows = [p for p in with_income["projections"] if p["age"] > 55]
        # The first several post-income years must show a positive corpus and no
        # unfunded expense, otherwise the income has not genuinely reseeded the
        # plan.
        self.assertEqual(
            [row["closing"] for row in after_income_rows[:6]],
            [5152000.0, 4650240.0, 4088268.8, 3458861.06, 2753924.38, 1964395.31],
        )
        self.assertTrue(all(row["unfunded_expense"] == 0.0 for row in after_income_rows[:6]))

        # Sanity: baseline was exhausted; the income reseeds the corpus so the
        # post-income trajectory differs materially from the baseline.
        baseline_closing_56 = next(p for p in baseline["projections"] if p["age"] == 56)["closing"]
        with_closing_56 = next(p for p in with_income["projections"] if p["age"] == 56)["closing"]
        self.assertGreater(with_closing_56, baseline_closing_56)

    def test_one_time_income_changes_min_corpus_and_required_returns(self):
        """Adding a future one-time income must change the planning/goal-seek
        metrics versus the identical baseline with no income.

        The forward projection already applies the income; this regression
        verifies the backward/goal-seek calculations (minimum-corpus and
        required pre/post returns) now also reflect that genuine future
        cash inflow.
        """
        base = PlannerInputs(
            current_age=30,
            retirement_age=60,
            life_expectancy=85,
            current_annual_expenses=800000,
            avg_inflation_rate=0.06,
            current_corpus=500000,
            annual_contribution=100000,
            pre_retirement_return=0.06,
            post_retirement_return=0.05,
            allocation_equity=0.60,
            allocation_debt=0.30,
            allocation_arbitrage=0.10,
            allocation_reit=0.0,
            equity_ltcg_split=0.70,
            equity_stcg_split=0.30,
            debt_portion_for_tax=0.30,
            arbitrage_portion_for_tax=0.10,
            reit_gains_fraction=0.0,
            tax_ltcg=0.125,
            tax_stcg=0.20,
            tax_debt=0.20,
            tax_arbitrage=0.20,
            ltcg_exemption=125000,
            reinvest_pension_surplus=False,
            include_pension=False,
            adhoc_expenses=[],
            one_time_incomes=[],
        )

        without_income = run_projection(base)
        with_income = run_projection(base.model_copy(update={
            "one_time_incomes": [OneTimeIncome(age=60, amount=2000000)],
        }))

        self.assertGreater(
            without_income["metrics"]["minimum_corpus_required"],
            with_income["metrics"]["minimum_corpus_required"],
            "One-time income must reduce minimum corpus required.",
        )
        self.assertGreater(
            without_income["metrics"]["gap_at_retirement"],
            with_income["metrics"]["gap_at_retirement"],
            "One-time income must reduce retirement gap.",
        )
        self.assertLess(
            without_income["metrics"]["readiness_percent"],
            with_income["metrics"]["readiness_percent"],
            "One-time income must improve readiness percent.",
        )

        # At least one of the required-return metrics must move in the
        # favorable direction when a genuine future income is available.
        without_pre = without_income["metrics"]["required_pre_retirement_return"]
        with_pre = with_income["metrics"]["required_pre_retirement_return"]
        without_post = without_income["metrics"]["required_post_retirement_return"]
        with_post = with_income["metrics"]["required_post_retirement_return"]

        self.assertTrue(
            with_pre < without_pre or with_post < without_post,
            "One-time income must reduce at least one required return metric.",
        )


if __name__ == "__main__":
    unittest.main()
