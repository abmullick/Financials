import unittest
from src.retirement_engine import run_projection, run_monte_carlo, _generate_recommendations, get_return_rate
from src.models import PlannerInputs, StressScenario, ReturnDistribution, AdHocExpense


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


if __name__ == "__main__":
    unittest.main()
