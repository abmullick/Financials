#!/usr/bin/env python3
"""
Auto-generated API test suite for retirement planner.
Tests multiple scenarios against the running server at http://localhost:20080/
"""

import json
import sys
import time
from pathlib import Path
import requests

BASE_URL = "http://localhost:20080"

def make_request(endpoint, payload):
    """Make API request and return (status_code, data_or_error)"""
    try:
        response = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=120)
        return response.status_code, response.json() if response.ok else response.text
    except Exception as e:
        return None, str(e)

def test_invalid_input(name, payload, expected_status=422):
    """Test that invalid inputs are properly rejected"""
    print(f"\n{'='*60}")
    print(f"TEST (INVALID): {name}")
    print(f"{'='*60}")
    status, result = make_request("/calculate", payload)
    
    if status is None:
        print(f"  ERROR: {result}")
        return False
    
    if status == expected_status:
        print(f"  Status       : REJECTED (HTTP {status})")
        print(f"  Response     : {str(result)[:200]}")
        return True
    else:
        print(f"  FAILED: Expected HTTP {expected_status}, got HTTP {status}")
        print(f"  Response: {str(result)[:500]}")
        return False

def test_invalid_mc_input(name, payload, expected_status=422):
    """Test that invalid inputs are properly rejected by MC endpoint"""
    print(f"\n{'='*60}")
    print(f"TEST (INVALID MC): {name}")
    print(f"{'='*60}")
    status, result = make_request("/calculate-mc", payload)
    
    if status is None:
        print(f"  ERROR: {result}")
        return False
    
    if status == expected_status:
        print(f"  Status       : REJECTED (HTTP {status})")
        print(f"  Response     : {str(result)[:200]}")
        return True
    else:
        print(f"  FAILED: Expected HTTP {expected_status}, got HTTP {status}")
        print(f"  Response: {str(result)[:500]}")
        return False

def test_deterministic(name, payload):
    """Test deterministic /calculate endpoint"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    status, result = make_request("/calculate", payload)
    
    if status is None:
        print(f"  ERROR: {result}")
        return False
    
    if status != 200:
        print(f"  FAILED: HTTP {status}")
        print(f"  Response: {result[:500]}")
        return False
    
    metrics = result.get("metrics", {})
    print(f"  Status       : SUCCESS")
    print(f"  Plan sustainable: {metrics.get('plan_sustainable')}")
    print(f"  Readiness %  : {metrics.get('readiness_percent', 'N/A')}")
    print(f"  Final corpus : {metrics.get('final_corpus', 'N/A')}")
    print(f"  Exhaustion age: {metrics.get('corpus_exhaustion_age', 'None')}")
    print(f"  Years in retirement: {metrics.get('years_in_retirement', 'N/A')}")
    print(f"  Projection rows: {len(result.get('projections', []))}")
    
    # Basic validation
    if not isinstance(metrics.get('plan_sustainable'), bool):
        print("  WARNING: plan_sustainable not a boolean")
        return False
    
    return True

def test_monte_carlo(name, payload):
    """Test Monte Carlo /calculate-mc endpoint"""
    print(f"\n{'='*60}")
    print(f"TEST (MC): {name}")
    print(f"{'='*60}")
    status, result = make_request("/calculate-mc", payload)
    
    if status is None:
        print(f"  ERROR: {result}")
        return False
    
    if status != 200:
        print(f"  FAILED: HTTP {status}")
        print(f"  Response: {result[:500]}")
        return False
    
    metrics = result.get("metrics", {})
    print(f"  Status       : SUCCESS")
    print(f"  Success rate : {metrics.get('success_rate', 'N/A')}%")
    print(f"  Median final : {metrics.get('median_final_corpus', 'N/A')}")
    print(f"  P5 final     : {metrics.get('p5_final_corpus', 'N/A')}")
    print(f"  P95 final    : {metrics.get('p95_final_corpus', 'N/A')}")
    print(f"  Simulations  : {result.get('num_simulations', 'N/A')}")
    print(f"  Yearly percentiles: {len(result.get('yearly_percentiles', {}).get('ages', []))} years")
    print(f"  Funding probability by age: {'Yes' if 'funding_probability_by_age' in result else 'No'}")
    print(f"  Failure ages : {'Yes' if 'failure_age_percentiles' in result else 'No'}")
    print(f"  Histogram    : {'Yes' if 'final_corpus_histogram' in result else 'No'}")
    print(f"  Recommendations: {len(result.get('recommendations', []))}")
    
    # Basic validation
    success_rate = metrics.get('success_rate', -1)
    if not (0 <= success_rate <= 100):
        print(f"  WARNING: success_rate out of range: {success_rate}")
        return False
    
    return True

# Base payload with defaults
BASE_PAYLOAD = {
    "current_age": 43,
    "retirement_age": 54,
    "life_expectancy": 90,
    "current_annual_expenses": 1200000,
    "avg_inflation_rate": 6.0,
    "current_corpus": 4000000,
    "annual_contribution": 700000,
    "pre_retirement_return": 9.0,
    "post_retirement_return": 8.0,
    "contribution_increase": 1.0,
    "ltcg_exemption": 125000,
    "one_time_lumpsum": 0,
    "stress_scenario": "Normal",
    "adhoc_expenses": [],
    "allocation_equity": 60,
    "allocation_debt": 30,
    "allocation_arbitrage": 10,
    "equity_ltcg_split": 70,
    "equity_stcg_split": 30,
    "tax_ltcg": 12.5,
    "tax_stcg": 20.0,
    "tax_debt": 20.0,
    "tax_arbitrage": 20.0,
    "include_pension": False,
    "pension_start_age": 60,
    "annual_pension": 600000,
    "pension_increase": 5.0,
    "pension_tax_rate": 20.0,
    "reinvest_pension_surplus": True
}

def deep_merge(base, override):
    """Deep merge override into base"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

# Test scenarios
TEST_SCENARIOS = [
    # 1. Base case - young professional
    ("Young professional, high growth", {
        "current_age": 23,
        "retirement_age": 58,
        "life_expectancy": 85,
        "current_annual_expenses": 600000,
        "current_corpus": 100000,
        "annual_contribution": 200000
    }),
    
    # 2. Near retirement, well funded
    ("Near retirement, well funded", {
        "current_age": 50,
        "retirement_age": 55,
        "life_expectancy": 80,
        "current_annual_expenses": 1500000,
        "current_corpus": 50000000,
        "annual_contribution": 0
    }),
    
    # 3. High expenses, low corpus - should exhaust
    ("High expenses, low corpus", {
        "current_age": 65,
        "retirement_age": 70,
        "life_expectancy": 75,
        "current_annual_expenses": 2000000,
        "current_corpus": 500000,
        "annual_contribution": 0,
        "post_retirement_return": 5.0
    }),
    
    # 4. With pension
    ("With pension income", {
        "current_age": 58,
        "retirement_age": 60,
        "life_expectancy": 82,
        "current_annual_expenses": 1200000,
        "current_corpus": 8000000,
        "annual_contribution": 300000,
        "include_pension": True,
        "pension_start_age": 60,
        "annual_pension": 800000,
        "pension_increase": 5.0,
        "pension_tax_rate": 15.0
    }),
    
    # 5. With ad-hoc expenses
    ("With ad-hoc expenses", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "annual_contribution": 300000,
        "adhoc_expenses": [
            {"age": 45, "amount": 1000000, "inflation_rate": 6.0},
            {"age": 55, "amount": 2000000, "inflation_rate": 6.0},
            {"age": 70, "amount": 500000, "inflation_rate": 6.0}
        ]
    }),
    
    # 6. Conservative portfolio
    ("Conservative portfolio", {
        "current_age": 45,
        "retirement_age": 60,
        "life_expectancy": 85,
        "current_annual_expenses": 800000,
        "current_corpus": 10000000,
        "annual_contribution": 500000,
        "allocation_equity": 30,
        "allocation_debt": 60,
        "allocation_arbitrage": 10,
        "pre_retirement_return": 8.0,
        "post_retirement_return": 6.0
    }),
    
    # 7. Aggressive portfolio
    ("Aggressive portfolio", {
        "current_age": 30,
        "retirement_age": 55,
        "life_expectancy": 85,
        "current_annual_expenses": 1000000,
        "current_corpus": 2000000,
        "annual_contribution": 400000,
        "allocation_equity": 80,
        "allocation_debt": 10,
        "allocation_arbitrage": 10,
        "pre_retirement_return": 12.0,
        "post_retirement_return": 10.0
    }),
    
    # 8. Stress scenario - mild crash
    ("Stress: mild crash", {
        "current_age": 55,
        "retirement_age": 58,
        "life_expectancy": 80,
        "current_annual_expenses": 1500000,
        "current_corpus": 20000000,
        "annual_contribution": 0,
        "stress_scenario": "Mild Crash (-10% for 2 yrs)"
    }),
    
    # 9. Stress scenario - severe crash
    ("Stress: severe crash", {
        "current_age": 55,
        "retirement_age": 58,
        "life_expectancy": 80,
        "current_annual_expenses": 1500000,
        "current_corpus": 15000000,
        "annual_contribution": 0,
        "stress_scenario": "Severe Crash (-20% for 2 yrs)"
    }),
    
    # 10. Zero inflation
    ("Zero inflation", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "avg_inflation_rate": 0.0,
        "current_corpus": 15000000,
        "annual_contribution": 500000
    }),
    
    # 11. With one-time lump sum
    ("With lump sum at retirement", {
        "current_age": 45,
        "retirement_age": 55,
        "life_expectancy": 80,
        "current_annual_expenses": 1200000,
        "current_corpus": 10000000,
        "annual_contribution": 400000,
        "one_time_lumpsum": 5000000
    }),
    
    # 12. Early retirement
    ("Early retirement", {
        "current_age": 40,
        "retirement_age": 50,
        "life_expectancy": 80,
        "current_annual_expenses": 1500000,
        "current_corpus": 30000000,
        "annual_contribution": 0
    }),
    
    # 13. Late retirement
    ("Late retirement", {
        "current_age": 50,
        "retirement_age": 65,
        "life_expectancy": 85,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "annual_contribution": 800000
    }),
    
    # 14. With correlations (Monte Carlo only)
    ("MC: With correlations", {
        "current_age": 35,
        "retirement_age": 55,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 8000000,
        "annual_contribution": 500000,
        "num_simulations": 100,
        "monte_carlo_seed": 42,
        "equity_debt_correlation": -0.2,
        "equity_arbitrage_correlation": 0.1,
        "debt_arbitrage_correlation": 0.3,
        "return_distribution": "lognormal"
    }, True),
    
    # 15. MC: Sensitivity analysis
    ("MC: Sensitivity analysis", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1200000,
        "current_corpus": 10000000,
        "annual_contribution": 400000,
        "num_simulations": 100,
        "monte_carlo_seed": 42,
        "retirement_age_sensitivity": [58, 62, 65]
    }, True),
    
    # 16. MC: Normal distribution
    ("MC: Normal distribution", {
        "current_age": 45,
        "retirement_age": 58,
        "life_expectancy": 80,
        "current_annual_expenses": 1200000,
        "current_corpus": 15000000,
        "annual_contribution": 300000,
        "num_simulations": 100,
        "monte_carlo_seed": 42,
        "return_distribution": "normal"
    }, True),
    
    # 17. Edge: Minimum valid ages
    ("Edge: Minimum valid ages", {
        "current_age": 1,
        "retirement_age": 2,
        "life_expectancy": 3,
        "current_annual_expenses": 100000,
        "current_corpus": 1000000,
        "annual_contribution": 50000,
        "avg_inflation_rate": 0.0
    }),
    
    # 18. Edge: Maximum valid ages
    ("Edge: Maximum valid ages", {
        "current_age": 100,
        "retirement_age": 110,
        "life_expectancy": 120,
        "current_annual_expenses": 500000,
        "current_corpus": 50000000,
        "annual_contribution": 0,
        "post_retirement_return": 0.0
    }),
    
    # 19. Edge: Zero contributions, zero corpus, high expenses (should exhaust)
    ("Edge: No savings, high burn", {
        "current_age": 30,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 5000000,
        "current_corpus": 0,
        "annual_contribution": 0,
        "avg_inflation_rate": 0.0,
        "post_retirement_return": 0.0
    }),
    
    # 20. Edge: Negative returns (allowed per model)
    ("Edge: Negative real returns", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 85,
        "current_annual_expenses": 1000000,
        "current_corpus": 20000000,
        "annual_contribution": 500000,
        "pre_retirement_return": -10.0,
        "post_retirement_return": -5.0,
        "avg_inflation_rate": 0.0
    }),
    
    # 21. Edge: Allocation sum validation (must equal 1.0)
    ("Edge: Allocation sum = 100%", {
        "current_age": 35,
        "retirement_age": 55,
        "life_expectancy": 85,
        "current_annual_expenses": 1200000,
        "current_corpus": 10000000,
        "annual_contribution": 400000,
        "allocation_equity": 50.0,
        "allocation_debt": 30.0,
        "allocation_arbitrage": 20.0
    }),
    
    # 22. Edge: Zero allocation to one category
    ("Edge: Zero debt allocation", {
        "current_age": 35,
        "retirement_age": 55,
        "life_expectancy": 85,
        "current_annual_expenses": 1200000,
        "current_corpus": 10000000,
        "annual_contribution": 400000,
        "allocation_equity": 70.0,
        "allocation_debt": 0.0,
        "allocation_arbitrage": 30.0
    }),
    
    # 23. Edge: Ad-hoc expenses at boundary ages
    ("Edge: Ad-hoc at current and life expectancy age", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "annual_contribution": 300000,
        "adhoc_expenses": [
            {"age": 40, "amount": 1000000, "inflation_rate": 5.0},
            {"age": 80, "amount": 2000000, "inflation_rate": 5.0}
        ]
    }),
    
    # 24. Edge: Pension starting immediately at retirement
    ("Edge: Pension at retirement age", {
        "current_age": 55,
        "retirement_age": 60,
        "life_expectancy": 85,
        "current_annual_expenses": 1200000,
        "current_corpus": 10000000,
        "annual_contribution": 0,
        "include_pension": True,
        "pension_start_age": 60,
        "annual_pension": 1000000,
        "pension_tax_rate": 10.0
    }),
    
    # 25. Edge: Maximum tax rate
    ("Edge: Maximum tax rates", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 10000000,
        "annual_contribution": 400000,
        "tax_ltcg": 100.0,
        "tax_stcg": 100.0,
        "tax_debt": 100.0,
        "tax_arbitrage": 100.0,
        "pension_tax_rate": 100.0
    }),
    
    # 26. Edge: Zero inflation and zero returns (preservation only)
    ("Edge: Zero inflation and returns", {
        "current_age": 45,
        "retirement_age": 55,
        "life_expectancy": 75,
        "current_annual_expenses": 1000000,
        "avg_inflation_rate": 0.0,
        "current_corpus": 20000000,
        "annual_contribution": 1000000,
        "pre_retirement_return": 0.0,
        "post_retirement_return": 0.0
    }),
    
    # 27. Edge: Very large corpus, very small expenses (high surplus)
    ("Edge: Very high surplus", {
        "current_age": 40,
        "retirement_age": 50,
        "life_expectancy": 70,
        "current_annual_expenses": 100000,
        "current_corpus": 1000000000,
        "annual_contribution": 10000000,
        "pre_retirement_return": 15.0
    }),
    
    # 28. Edge: Ad-hoc expense with no specific inflation
    ("Edge: Ad-hoc with default inflation", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "annual_contribution": 300000,
        "adhoc_expenses": [
            {"age": 50, "amount": 2000000}
        ]
    }),
    
    # 29. Edge: Stress with zero corpus
    ("Edge: Stress crash with zero corpus", {
        "current_age": 55,
        "retirement_age": 58,
        "life_expectancy": 80,
        "current_annual_expenses": 1500000,
        "current_corpus": 0,
        "annual_contribution": 0,
        "stress_scenario": "Severe Crash (-20% for 2 yrs)"
    }),
    
    # 30. Edge: MC with minimum simulations
    ("Edge: MC minimum simulations", {
        "current_age": 35,
        "retirement_age": 55,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 8000000,
        "annual_contribution": 500000,
        "num_simulations": 100,
        "monte_carlo_seed": 42,
        "return_distribution": "lognormal"
    }, True),
    
    # 31. Edge: MC with extreme correlations
    ("Edge: MC extreme correlations", {
        "current_age": 35,
        "retirement_age": 55,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 8000000,
        "annual_contribution": 500000,
        "num_simulations": 100,
        "monte_carlo_seed": 42,
        "equity_debt_correlation": 1.0,
        "equity_arbitrage_correlation": -1.0,
        "debt_arbitrage_correlation": 0.0,
        "return_distribution": "normal"
    }, True),
    
    # 32. Edge: MC with high volatility
    ("Edge: MC high volatility", {
        "current_age": 35,
        "retirement_age": 55,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 8000000,
        "annual_contribution": 500000,
        "num_simulations": 100,
        "monte_carlo_seed": 42,
        "volatility_equity": 0.50,
        "volatility_debt": 0.30,
        "volatility_arbitrage": 0.40,
        "return_distribution": "lognormal"
    }, True),
    
    # 33. Edge: Sensitivity with single age
    ("Edge: MC single sensitivity age", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1200000,
        "current_corpus": 10000000,
        "annual_contribution": 400000,
        "num_simulations": 100,
        "monte_carlo_seed": 42,
        "retirement_age_sensitivity": [55]
    }, True),
    
    # 34. Edge: Sensitivity with same age as base
    ("Edge: MC same sensitivity age", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1200000,
        "current_corpus": 10000000,
        "annual_contribution": 400000,
        "num_simulations": 100,
        "monte_carlo_seed": 42,
        "retirement_age_sensitivity": [60]
    }, True),
    
    # 35. Edge: LTCG exemption at boundary
    ("Edge: LTCG exemption at max", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "annual_contribution": 300000,
        "ltcg_exemption": 10000000
    }),
]

# Invalid input test scenarios - these should all be rejected
INVALID_TEST_SCENARIOS = [
    # Validation rule violations
    ("Invalid: Retirement age <= current age", {
        "current_age": 60,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
    }),
    
    ("Invalid: Life expectancy < retirement age", {
        "current_age": 40,
        "retirement_age": 70,
        "life_expectancy": 65,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
    }),
    
    ("Invalid: Negative current age", {
        "current_age": -5,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
    }),
    
    ("Invalid: Negative expenses", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": -100000,
        "current_corpus": 5000000,
    }),
    
    ("Invalid: Negative corpus", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": -1000000,
    }),
    
    ("Invalid: Inflation rate exceeds max (0.5)", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "avg_inflation_rate": 0.6,
    }),
    
    ("Invalid: Return rate exceeds max (0.5)", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "pre_retirement_return": 0.6,
    }),
    
    ("Invalid: Return rate below min (-0.5)", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "pre_retirement_return": -0.6,
    }),
    
    ("Invalid: Portfolio allocation sum > 100%", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "allocation_equity": 60.0,
        "allocation_debt": 30.0,
        "allocation_arbitrage": 20.0,
    }),
    
    ("Invalid: Portfolio allocation sum < 100%", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "allocation_equity": 50.0,
        "allocation_debt": 30.0,
        "allocation_arbitrage": 10.0,
    }),
    
    ("Invalid: Equity split sum != 100%", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "equity_ltcg_split": 0.5,
        "equity_stcg_split": 0.3,
    }),
    
    ("Invalid: Ad-hoc expense age before current age", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "adhoc_expenses": [
            {"age": 30, "amount": 1000000, "inflation_rate": 5.0}
        ]
    }),
    
    ("Invalid: Ad-hoc expense age after life expectancy", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "adhoc_expenses": [
            {"age": 85, "amount": 1000000, "inflation_rate": 5.0}
        ]
    }),
    
    ("Invalid: Duplicate ad-hoc expense ages", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "adhoc_expenses": [
            {"age": 50, "amount": 1000000, "inflation_rate": 5.0},
            {"age": 50, "amount": 2000000, "inflation_rate": 5.0}
        ]
    }),
    
    ("Invalid: Pension start age in the past", {
        "current_age": 60,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "include_pension": True,
        "pension_start_age": 50,
        "annual_pension": 500000,
    }),
    
    ("Invalid: Pension start age after life expectancy", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "include_pension": True,
        "pension_start_age": 85,
        "annual_pension": 500000,
    }),
    
    ("Invalid: Zero pension when pension included", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "include_pension": True,
        "pension_start_age": 60,
        "annual_pension": 0,
    }),
    
    ("Invalid: Negative pension when pension included", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "include_pension": True,
        "pension_start_age": 60,
        "annual_pension": -100000,
    }),
    
    ("Invalid: Invalid stress scenario", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "stress_scenario": "Mega Crash (-50% for 5 yrs)",
    }),
    
    ("Invalid: Invalid return distribution", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "return_distribution": "poisson",
    }),
    
    ("Invalid: MC simulations below minimum", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "num_simulations": 50,
    }),
    
    ("Invalid: MC simulations above maximum", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "num_simulations": 100000,
    }),
    
    ("Invalid: Correlation above 1.0", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "equity_debt_correlation": 1.5,
    }),
    
    ("Invalid: Correlation below -1.0", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "equity_debt_correlation": -1.5,
    }),
    
    ("Invalid: Volatility above 1.0", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "volatility_equity": 1.5,
    }),
    
    ("Invalid: Negative volatility", {
        "current_age": 40,
        "retirement_age": 60,
        "life_expectancy": 80,
        "current_annual_expenses": 1000000,
        "current_corpus": 5000000,
        "volatility_equity": -0.1,
    }),
]

# Remember the original number of valid scenarios
original_valid_count = len(TEST_SCENARIOS)

# REIT-specific valid scenarios
REIT_VALID_SCENARIOS = [
    # Deterministic REIT scenarios
    ("REIT allocation 20%", {"allocation_reit": 0.20}, False),
    ("REIT return 12%", {"return_reit": 0.12}, False),
    ("REIT gain fraction 0.0", {"reit_gain_fraction": 0.0}, False),
    ("REIT gain fraction 1.0", {"reit_gain_fraction": 1.0}, False),
    # Monte Carlo REIT scenarios
    ("REIT MC allocation 20%", {"allocation_reit": 0.20, "num_simulations": 100, "monte_carlo_seed": 42}, True),
    ("REIT MC gain fraction 0.0", {"allocation_reit": 0.20, "reit_gain_fraction": 0.0, "num_simulations": 100, "monte_carlo_seed": 42}, True),
    ("REIT MC gain fraction 1.0", {"allocation_reit": 0.20, "reit_gain_fraction": 1.0, "num_simulations": 100, "monte_carlo_seed": 42}, True),
]

# Extend the existing TEST_SCENARIOS with REIT scenarios
TEST_SCENARIOS.extend(REIT_VALID_SCENARIOS)


def test_reit_behavior():
    """Test REIT-specific behavioral regression by comparing API responses with different REIT parameters."""
    print("\n" + "="*60)
    print("REIT BEHAVIORAL REGRESSION TESTS")
    print("="*60)
    
    # Use the same base payload for all comparisons
    base_payload = deep_merge(BASE_PAYLOAD, {})
    
    # Convert percentage inputs to decimal fractions (frontend does this before sending)
    percentage_fields = [
        "avg_inflation_rate", "pre_retirement_return", "post_retirement_return",
        "contribution_increase", "pension_increase", "pension_tax_rate",
        "tax_ltcg", "tax_stcg", "tax_debt", "tax_arbitrage",
        "allocation_equity", "allocation_debt", "allocation_arbitrage",
        "equity_ltcg_split", "equity_stcg_split"
    ]
    for key in percentage_fields:
        if key in base_payload and isinstance(base_payload[key], (int, float)):
            base_payload[key] = base_payload[key] / 100.0
    
    # Convert ad-hoc expense inflation rates from percentages to decimals
    if "adhoc_expenses" in base_payload and isinstance(base_payload["adhoc_expenses"], list):
        for expense in base_payload["adhoc_expenses"]:
            if isinstance(expense, dict) and "inflation_rate" in expense and isinstance(expense["inflation_rate"], (int, float)):
                expense["inflation_rate"] = expense["inflation_rate"] / 100.0
    
    # Track test results
    reit_tests_passed = 0
    reit_tests_failed = 0
    
    # 1. REIT allocation: Compare allocation_reit=0.0 vs allocation_reit=0.20
    print("\n1. Testing REIT allocation effect...")
    payload_no_reit = deep_merge(base_payload, {"allocation_reit": 0.0})
    payload_with_reit = deep_merge(base_payload, {"allocation_reit": 0.20})
    
    status1, result1 = make_request("/calculate", payload_no_reit)
    status2, result2 = make_request("/calculate", payload_with_reit)
    
    if status1 == 200 and status2 == 200:
        # Compare final corpus or readiness percent
        corp1 = result1.get("metrics", {}).get("final_corpus", 0)
        corp2 = result2.get("metrics", {}).get("final_corpus", 0)
        if corp1 != corp2:
            print(f"   PASS: Final corpus changed from {corp1:.2f} to {corp2:.2f} with 20% REIT allocation")
            reit_tests_passed += 1
        else:
            print(f"   FAIL: Final corpus did not change with REIT allocation (both {corp1:.2f})")
            reit_tests_failed += 1
    else:
        print(f"   FAIL: API error - status1={status1}, status2={status2}")
        reit_tests_failed += 1
    
    # 2. REIT return: With allocation_reit=0.20, compare return_reit=0.08 vs 0.12
    print("\n2. Testing REIT return effect...")
    payload_low_return = deep_merge(base_payload, {"allocation_reit": 0.20, "return_reit": 0.08})
    payload_high_return = deep_merge(base_payload, {"allocation_reit": 0.20, "return_reit": 0.12})
    
    status1, result1 = make_request("/calculate", payload_low_return)
    status2, result2 = make_request("/calculate", payload_high_return)
    
    if status1 == 200 and status2 == 200:
        # Higher REIT return should lead to higher final corpus
        corp1 = result1.get("metrics", {}).get("final_corpus", 0)
        corp2 = result2.get("metrics", {}).get("final_corpus", 0)
        if corp2 > corp1:
            print(f"   PASS: Final corpus increased from {corp1:.2f} to {corp2:.2f} with higher REIT return")
            reit_tests_passed += 1
        else:
            print(f"   FAIL: Final corpus did not increase with higher REIT return ({corp1:.2f} -> {corp2:.2f})")
            reit_tests_failed += 1
    else:
        print(f"   FAIL: API error - status1={status1}, status2={status2}")
        reit_tests_failed += 1
    
    # 3. REIT taxable gain fraction: Compare reit_gain_fraction=0.0 vs 1.0
    print("\n3. Testing REIT taxable gain fraction effect...")
    payload_no_gain = deep_merge(base_payload, {"allocation_reit": 0.20, "reit_gain_fraction": 0.0})
    payload_all_gain = deep_merge(base_payload, {"allocation_reit": 0.20, "reit_gain_fraction": 1.0})
    
    status1, result1 = make_request("/calculate", payload_no_gain)
    status2, result2 = make_request("/calculate", payload_all_gain)
    
    if status1 == 200 and status2 == 200:
        # Higher taxable gain fraction should lead to lower final corpus (more taxes)
        corp1 = result1.get("metrics", {}).get("final_corpus", 0)
        corp2 = result2.get("metrics", {}).get("final_corpus", 0)
        if corp2 < corp1:
            print(f"   PASS: Final corpus decreased from {corp1:.2f} to {corp2:.2f} with full REIT taxation")
            reit_tests_passed += 1
        else:
            print(f"   FAIL: Final corpus did not decrease with full REIT taxation ({corp1:.2f} -> {corp2:.2f})")
            reit_tests_failed += 1
    else:
        print(f"   FAIL: API error - status1={status1}, status2={status2}")
        reit_tests_failed += 1
    
    # 4. MC REIT allocation: Compare allocation_reit=0.0 vs 0.20
    print("\n4. Testing MC REIT allocation effect...")
    mc_seed = 42
    mc_sims = 100
    payload_no_reit_mc = deep_merge(base_payload, {
        "allocation_reit": 0.0,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    payload_with_reit_mc = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    
    status1, result1 = make_request("/calculate-mc", payload_no_reit_mc)
    status2, result2 = make_request("/calculate-mc", payload_with_reit_mc)
    
    if status1 == 200 and status2 == 200:
        # Compare success rate or median final corpus
        success1 = result1.get("metrics", {}).get("success_rate", 0)
        success2 = result2.get("metrics", {}).get("success_rate", 0)
        if success1 != success2:
            print(f"   PASS: MC success rate changed from {success1:.1f}% to {success2:.1f}% with 20% REIT allocation")
            reit_tests_passed += 1
        else:
            # Try median final corpus
            med1 = result1.get("metrics", {}).get("median_final_corpus", 0)
            med2 = result2.get("metrics", {}).get("median_final_corpus", 0)
            if med1 != med2:
                print(f"   PASS: MC median final corpus changed from {med1:.2f} to {med2:.2f} with 20% REIT allocation")
                reit_tests_passed += 1
            else:
                print(f"   FAIL: MC results did not change with REIT allocation")
                reit_tests_failed += 1
    else:
        print(f"   FAIL: API error - status1={status1}, status2={status2}")
        reit_tests_failed += 1
    
    # 5. MC REIT taxable gain fraction: Compare reit_gain_fraction=0.0 vs 1.0
    print("\n5. Testing MC REIT taxable gain fraction effect...")
    payload_no_gain_mc = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "reit_gain_fraction": 0.0,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    payload_all_gain_mc = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "reit_gain_fraction": 1.0,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    
    status1, result1 = make_request("/calculate-mc", payload_no_gain_mc)
    status2, result2 = make_request("/calculate-mc", payload_all_gain_mc)
    
    if status1 == 200 and status2 == 200:
        # Higher taxable gain fraction should lead to lower success rate (more taxes)
        success1 = result1.get("metrics", {}).get("success_rate", 0)
        success2 = result2.get("metrics", {}).get("success_rate", 0)
        if success2 < success1:
            print(f"   PASS: MC success rate decreased from {success1:.1f}% to {success2:.1f}% with full REIT taxation")
            reit_tests_passed += 1
        else:
            print(f"   FAIL: MC success rate did not decrease with full REIT taxation ({success1:.1f}% -> {success2:.1f}%)")
            reit_tests_failed += 1
    else:
        print(f"   FAIL: API error - status1={status1}, status2={status2}")
        reit_tests_failed += 1
    
    # 6. MC volatility: Compare volatility_reit=0.15 vs 0.25
    print("\n6. Testing MC REIT volatility effect...")
    payload_low_vol = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "volatility_reit": 0.15,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    payload_high_vol = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "volatility_reit": 0.25,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    
    status1, result1 = make_request("/calculate-mc", payload_low_vol)
    status2, result2 = make_request("/calculate-mc", payload_high_vol)
    
    if status1 == 200 and status2 == 200:
        # Higher volatility should lead to lower success rate (more risk)
        success1 = result1.get("metrics", {}).get("success_rate", 0)
        success2 = result2.get("metrics", {}).get("success_rate", 0)
        if success2 < success1:
            print(f"   PASS: MC success rate decreased from {success1:.1f}% to {success2:.1f}% with higher REIT volatility")
            reit_tests_passed += 1
        else:
            print(f"   FAIL: MC success rate did not decrease with higher REIT volatility ({success1:.1f}% -> {success2:.1f}%)")
            reit_tests_failed += 1
    else:
        print(f"   FAIL: API error - status1={status1}, status2={status2}")
        reit_tests_failed += 1
    
    # 7. MC correlations: Test each REIT correlation independently
    print("\n7. Testing MC REIT correlations effect...")
    correlations_tested = 0
    correlations_passed = 0
    
    # Test equity_reit_correlation
    print("   Testing equity_reit_correlation...")
    payload_low_corr = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "equity_reit_correlation": 0.0,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    payload_high_corr = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "equity_reit_correlation": 0.8,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    
    status1, result1 = make_request("/calculate-mc", payload_low_corr)
    status2, result2 = make_request("/calculate-mc", payload_high_corr)
    
    if status1 == 200 and status2 == 200:
        success1 = result1.get("metrics", {}).get("success_rate", 0)
        success2 = result2.get("metrics", {}).get("success_rate", 0)
        if success1 != success2:
            print(f"      PASS: Equity-REIT correlation affects MC results ({success1:.1f}% -> {success2:.1f}%)")
            correlations_passed += 1
        else:
            print(f"      FAIL: Equity-REIT correlation does not affect MC results")
    else:
        print(f"      FAIL: API error - status1={status1}, status2={status2}")
    correlations_tested += 1
    
    # Test debt_reit_correlation
    print("   Testing debt_reit_correlation...")
    payload_low_corr = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "debt_reit_correlation": 0.0,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    payload_high_corr = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "debt_reit_correlation": 0.8,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    
    status1, result1 = make_request("/calculate-mc", payload_low_corr)
    status2, result2 = make_request("/calculate-mc", payload_high_corr)
    
    if status1 == 200 and status2 == 200:
        success1 = result1.get("metrics", {}).get("success_rate", 0)
        success2 = result2.get("metrics", {}).get("success_rate", 0)
        if success1 != success2:
            print(f"      PASS: Debt-REIT correlation affects MC results ({success1:.1f}% -> {success2:.1f}%)")
            correlations_passed += 1
        else:
            print(f"      FAIL: Debt-REIT correlation does not affect MC results")
    else:
        print(f"      FAIL: API error - status1={status1}, status2={status2}")
    correlations_tested += 1
    
    # Test arbitrage_reit_correlation
    print("   Testing arbitrage_reit_correlation...")
    payload_low_corr = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "arbitrage_reit_correlation": 0.0,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    payload_high_corr = deep_merge(base_payload, {
        "allocation_reit": 0.20,
        "arbitrage_reit_correlation": 0.8,
        "num_simulations": mc_sims,
        "monte_carlo_seed": mc_seed
    })
    
    status1, result1 = make_request("/calculate-mc", payload_low_corr)
    status2, result2 = make_request("/calculate-mc", payload_high_corr)
    
    if status1 == 200 and status2 == 200:
        success1 = result1.get("metrics", {}).get("success_rate", 0)
        success2 = result2.get("metrics", {}).get("success_rate", 0)
        if success1 != success2:
            print(f"      PASS: Arbitrage-REIT correlation affects MC results ({success1:.1f}% -> {success2:.1f}%)")
            correlations_passed += 1
        else:
            print(f"      FAIL: Arbitrage-REIT correlation does not affect MC results")
    else:
        print(f"      FAIL: API error - status1={status1}, status2={status2}")
    correlations_tested += 1
    
    if correlations_passed == correlations_tested:
        print(f"   PASS: All {correlations_tested} REIT correlation tests passed")
        reit_tests_passed += correlations_passed
    else:
        print(f"   FAIL: {correlations_passed}/{correlations_tested} REIT correlation tests passed")
        reit_tests_failed += (correlations_tested - correlations_passed)
    
    # Summary
    print(f"\nREIT Behavioral Tests Summary:")
    print(f"  Passed: {reit_tests_passed}")
    print(f"  Failed: {reit_tests_failed}")
    print(f"  Total:  {reit_tests_passed + reit_tests_failed}")
    
    return reit_tests_failed == 0


def main():
    print("="*60)
    print("RETIREMENT PLANNER API TEST SUITE")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Total scenarios: {len(TEST_SCENARIOS) + len(INVALID_TEST_SCENARIOS)} ({original_valid_count} valid + {len(REIT_VALID_SCENARIOS)} REIT valid + {len(INVALID_TEST_SCENARIOS)} invalid)")
    print(f"Plus: 1 REIT behavioral test suite (7 comparisons)")
    
    results = {
        "deterministic": {"passed": 0, "failed": 0, "tests": []},
        "monte_carlo": {"passed": 0, "failed": 0, "tests": []},
        "invalid": {"passed": 0, "failed": 0, "tests": []}
    }
    
    for scenario in TEST_SCENARIOS:
        if len(scenario) == 3:
            name, overrides, is_mc = scenario
        else:
            name, overrides = scenario
            is_mc = False
        
        payload = deep_merge(BASE_PAYLOAD, overrides)
        
        # Convert percentage inputs to decimal fractions (frontend does this before sending)
        percentage_fields = [
            "avg_inflation_rate", "pre_retirement_return", "post_retirement_return",
            "contribution_increase", "pension_increase", "pension_tax_rate",
            "tax_ltcg", "tax_stcg", "tax_debt", "tax_arbitrage",
            "allocation_equity", "allocation_debt", "allocation_arbitrage",
            "equity_ltcg_split", "equity_stcg_split"
        ]
        for key in percentage_fields:
            if key in payload and isinstance(payload[key], (int, float)):
                payload[key] = payload[key] / 100.0
        
        # Convert ad-hoc expense inflation rates from percentages to decimals
        if "adhoc_expenses" in payload and isinstance(payload["adhoc_expenses"], list):
            for expense in payload["adhoc_expenses"]:
                if isinstance(expense, dict) and "inflation_rate" in expense and isinstance(expense["inflation_rate"], (int, float)):
                    expense["inflation_rate"] = expense["inflation_rate"] / 100.0
        
        if is_mc:
            passed = test_monte_carlo(name, payload)
            results["monte_carlo"]["tests"].append((name, passed))
            if passed:
                results["monte_carlo"]["passed"] += 1
            else:
                results["monte_carlo"]["failed"] += 1
            time.sleep(1)  # Brief pause between MC tests
        else:
            passed = test_deterministic(name, payload)
            results["deterministic"]["tests"].append((name, passed))
            if passed:
                results["deterministic"]["passed"] += 1
            else:
                results["deterministic"]["failed"] += 1
            time.sleep(7)  # Stay under /calculate rate limit (10/min)
    
# Run invalid input tests
    for name, overrides in INVALID_TEST_SCENARIOS:
        payload = deep_merge(BASE_PAYLOAD, overrides)
        
        passed = test_invalid_input(name, payload)
        results["invalid"]["tests"].append((name, passed))
        if passed:
            results["invalid"]["passed"] += 1
        else:
            results["invalid"]["failed"] += 1
        time.sleep(1)  # Brief pause between validation tests
    
    # Run REIT behavioral tests
    reit_behavior_passed = test_reit_behavior()
    if reit_behavior_passed:
        results["reit_behavior"] = {"passed": 1, "failed": 0}
    else:
        results["reit_behavior"] = {"passed": 0, "failed": 1}

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"\nDeterministic (/calculate):")
    print(f"  Passed: {results['deterministic']['passed']}")
    print(f"  Failed: {results['deterministic']['failed']}")
    if results['deterministic']['failed'] > 0:
        print("  Failed tests:")
        for name, passed in results['deterministic']['tests']:
            if not passed:
                print(f"    - {name}")
    
    print(f"\nMonte Carlo (/calculate-mc):")
    print(f"  Passed: {results['monte_carlo']['passed']}")
    print(f"  Failed: {results['monte_carlo']['failed']}")
    if results['monte_carlo']['failed'] > 0:
        print("  Failed tests:")
        for name, passed in results['monte_carlo']['tests']:
            if not passed:
                print(f"    - {name}")
                
    print(f"\nREIT Behavioral Tests:")
    print(f"  Passed: {results['reit_behavior']['passed']}")
    print(f"  Failed: {results['reit_behavior']['failed']}")
    
    print(f"\nInvalid Input Validation:")
    print(f"  Passed: {results['invalid']['passed']}")
    print(f"  Failed: {results['invalid']['failed']}")
    if results['invalid']['failed'] > 0:
        print("  Failed tests:")
        for name, passed in results['invalid']['tests']:
            if not passed:
                print(f"    - {name}")
    
    total = results['deterministic']['passed'] + results['deterministic']['failed'] + results['monte_carlo']['passed'] + results['monte_carlo']['failed'] + results['invalid']['passed'] + results['invalid']['failed'] + results['reit_behavior']['passed'] + results['reit_behavior']['failed']
    print(f"\nOverall: {results['deterministic']['passed'] + results['monte_carlo']['passed'] + results['invalid']['passed'] + results['reit_behavior']['passed']}/{total} passed")
    
    # Exit with error code if any failures
    if results['deterministic']['failed'] > 0 or results['monte_carlo']['failed'] > 0 or results['invalid']['failed'] > 0 or results['reit_behavior']['failed'] > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
