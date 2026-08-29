"""
Tests for the AI Insights endpoint and models.

All provider API calls are mocked. These tests must not require GROQ_API_KEY,
GEMINI_API_KEY, internet access, provider quota, availability, or rate limits.
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.models import PlannerInputs
from src.ai_insights import (
    AIInsightRequest,
    AIInsightResponse,
    PredictiveAnalysisSummary,
    MonteCarloAnalysisSummary,
    MethodologyContext,
    OverallAssessment,
    DeterministicInterpretation,
    MonteCarloInterpretation,
    Comparison,
    CashFlowInsights,
    RiskItem,
    ActionItem,
    _get_groq_config,
    _get_gemini_config,
    _get_provider_config,
    _call_groq,
    _call_gemini,
    _extract_json_from_text,
    _build_compact_prompt,
    _compact_funding_probability,
    AIInsightService,
)
from groq import RateLimitError, APIStatusError, APIConnectionError, BadRequestError
from google import genai


def _make_request(**overrides):
    base_inputs = {
        "current_age": 43,
        "retirement_age": 54,
        "life_expectancy": 90,
        "current_annual_expenses": 1200000,
        "avg_inflation_rate": 0.06,
        "current_corpus": 4000000,
        "annual_contribution": 700000,
        "pre_retirement_return": 0.09,
        "post_retirement_return": 0.08,
        "contribution_increase": 0.01,
        "ltcg_exemption": 125000,
        "one_time_lumpsum": 0,
        "stress_scenario": "Normal",
        "adhoc_expenses": [
            {"age": 58, "amount": 2500000, "inflation_rate": None},
            {"age": 75, "amount": 1000000, "inflation_rate": None}
        ],
        "allocation_equity": 0.60,
        "allocation_debt": 0.30,
        "allocation_arbitrage": 0.10,
        "equity_ltcg_split": 0.70,
        "equity_stcg_split": 0.30,
        "tax_ltcg": 0.125,
        "tax_stcg": 0.20,
        "tax_debt": 0.20,
        "tax_arbitrage": 0.20,
        "include_pension": False,
        "pension_start_age": 60,
        "annual_pension": 600000,
        "pension_increase": 0.05,
        "pension_tax_rate": 0.20,
        "reinvest_pension_surplus": True,
        "num_simulations": 1000,
        "volatility_equity": 0.18,
        "volatility_debt": 0.06,
        "volatility_arbitrage": 0.08,
        "equity_debt_correlation": -0.10,
        "equity_arbitrage_correlation": 0.05,
        "debt_arbitrage_correlation": 0.20,
        "return_distribution": "lognormal",
        "monte_carlo_seed": None,
        "retirement_age_sensitivity": None,
    }
    base_inputs.update(overrides)
    return base_inputs


def _make_payload(**overrides):
    payload = {
        "user_inputs": _make_request(),
        "predictive_analysis": {
            "readiness_percent": 95.18,
            "plan_sustainable": False,
            "corpus_at_retirement": 152960169.0,
            "minimum_corpus_required": 160709753.0,
            "gap_at_retirement": 7749583.0,
            "years_in_retirement": 25,
            "corpus_exhaustion_age": None,
            "total_contributions": 25000000.0,
            "total_pension_received": 0.0,
            "average_pension_coverage": 0.0,
            "required_pre_retirement_return": 10.32,
            "required_post_retirement_return": 8.47
        },
        "monte_carlo_analysis": {
            "success_rate": 33.0,
            "median_final_corpus": 0.0,
            "mean_final_corpus": 50000000.0,
            "std_final_corpus": 150000000.0,
            "p5_final_corpus": 0.0,
            "p95_final_corpus": 468095519.0,
            "failure_age_percentiles": {"p50": 77, "p75": 80},
            "funding_probability_by_age": {"60": 100.0, "65": 85.0, "70": 60.0, "75": 35.0, "80": 15.0},
            "final_corpus_histogram": {"labels": ["₹0-₹10L", "₹10L-₹20L"], "probabilities": [45.0, 20.0]},
            "num_simulations": 100,
            "retirement_age_sensitivity": {"58": {"success_rate": 28.0, "median_final_corpus": 0.0}, "62": {"success_rate": 45.0, "median_final_corpus": 25000000.0}},
            "existing_recommendations": [
                "Your plan has a high risk of running out of money.",
                "Plan becomes fragile around age 77."
            ]
        },
        "methodology": {
            "success_definition": "A simulation is successful if the portfolio funds all required expenses through life expectancy without depletion.",
            "failure_definition": "A simulation fails if the corpus reaches zero before life expectancy and an expense cannot be fully funded.",
            "percentile_explanation": "The 5th percentile is exceeded by 95% of paths.",
            "funding_probability_explanation": "The probability that expenses are fully funded in a particular year.",
            "recommended_success_threshold": "Target 80-90% for moderate risk tolerance."
        }
    }
    payload.update(overrides)
    return payload


def _mock_gemini_response():
    return MagicMock(
        text=json.dumps({
            "overall_assessment": {
                "rating": "moderate",
                "headline": "Plan faces a moderate risk of shortfall.",
                "summary": "Your baseline projection indicates a gap, but the Monte Carlo analysis shows the plan remains viable in many scenarios. The largest vulnerability is the combination of early retirement and large planned expenses."
            },
            "deterministic_interpretation": {
                "assessment": "The deterministic projection shows a gap between projected corpus and required corpus.",
                "key_points": [
                    "Projected corpus at retirement is below the minimum required.",
                    "Corpus is expected to exhaust around age 77 under baseline assumptions."
                ]
            },
            "monte_carlo_interpretation": {
                "assessment": "Monte Carlo results indicate significant uncertainty around the deterministic outcome.",
                "key_points": [
                    "33% of simulated paths succeed through life expectancy.",
                    "The 5th percentile final corpus is zero, indicating tail risk."
                ]
            },
            "comparison": {
                "what_deterministic_shows": "A single projected path that ends in shortfall.",
                "what_monte_carlo_adds": "A distribution of outcomes showing that some paths succeed and others fail.",
                "why_the_results_differ": "Deterministic uses average returns; Monte Carlo accounts for volatility and sequence-of-returns risk."
            },
            "cash_flow_insights": {
                "pension": "Pension income starts at age 60 and covers a portion of recurring expenses.",
                "adhoc_expenses": "Large ad-hoc expenses at ages 58 and 75 create concentrated cash-flow needs.",
                "one_time_retirement_income": "No additional lumpsum is assumed at retirement.",
                "retirement_expenses": "Expenses grow with inflation, increasing pressure on the corpus over time."
            },
            "strengths": [
                "Regular contributions build a meaningful corpus.",
                "Pension income provides a stable floor in retirement."
            ],
            "risks": [
                {
                    "severity": "high",
                    "risk": "Corpus exhaustion in late retirement",
                    "explanation": "Both deterministic and Monte Carlo analyses indicate a meaningful risk of running out of funds before life expectancy."
                },
                {
                    "severity": "medium",
                    "risk": "Ad-hoc expense timing",
                    "explanation": "Large planned expenses coincide with retirement, reducing the available buffer."
                }
            ],
            "key_insights": [
                "The plan is fragile under baseline assumptions.",
                "Increasing contributions or delaying retirement would materially improve outcomes."
            ],
            "actions": [
                {
                    "action": "Increase annual contributions",
                    "reason": "Higher contributions would close the projected gap and improve the Monte Carlo success rate."
                },
                {
                    "action": "Consider delaying retirement",
                    "reason": "Delaying retirement reduces the withdrawal period and allows more accumulation."
                }
            ],
            "assumption_warnings": [
                "Returns are assumed to follow a lognormal distribution with constant volatility.",
                "Inflation and contribution growth are held constant."
            ],
            "bottom_line": "Your retirement plan carries moderate-to-high risk under current assumptions. The deterministic projection shows a shortfall, and Monte Carlo confirms that market volatility can exhaust the corpus by age 77. Increasing savings, delaying retirement, or reducing planned expenses would meaningfully improve your odds."
        })
    )


def _mock_groq_response():
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "overall_assessment": {
            "rating": "moderate",
            "headline": "Plan faces a moderate risk of shortfall.",
            "summary": "Your baseline projection indicates a gap, but the Monte Carlo analysis shows the plan remains viable in many scenarios. The largest vulnerability is the combination of early retirement and large planned expenses."
        },
        "deterministic_interpretation": {
            "assessment": "The deterministic projection shows a gap between projected corpus and required corpus.",
            "key_points": [
                "Projected corpus at retirement is below the minimum required.",
                "Corpus is expected to exhaust around age 77 under baseline assumptions."
            ]
        },
        "monte_carlo_interpretation": {
            "assessment": "Monte Carlo results indicate significant uncertainty around the deterministic outcome.",
            "key_points": [
                "33% of simulated paths succeed through life expectancy.",
                "The 5th percentile final corpus is zero, indicating tail risk."
            ]
        },
        "comparison": {
            "what_deterministic_shows": "A single projected path that ends in shortfall.",
            "what_monte_carlo_adds": "A distribution of outcomes showing that some paths succeed and others fail.",
            "why_the_results_differ": "Deterministic uses average returns; Monte Carlo accounts for volatility and sequence-of-returns risk."
        },
        "cash_flow_insights": {
            "pension": "Pension income starts at age 60 and covers a portion of recurring expenses.",
            "adhoc_expenses": "Large ad-hoc expenses at ages 58 and 75 create concentrated cash-flow needs.",
            "one_time_retirement_income": "No additional lumpsum is assumed at retirement.",
            "retirement_expenses": "Expenses grow with inflation, increasing pressure on the corpus over time."
        },
        "strengths": [
            "Regular contributions build a meaningful corpus.",
            "Pension income provides a stable floor in retirement."
        ],
        "risks": [
            {
                "severity": "high",
                "risk": "Corpus exhaustion in late retirement",
                "explanation": "Both deterministic and Monte Carlo analyses indicate a meaningful risk of running out of funds before life expectancy."
            },
            {
                "severity": "medium",
                "risk": "Ad-hoc expense timing",
                "explanation": "Large planned expenses coincide with retirement, reducing the available buffer."
            }
        ],
        "key_insights": [
            "The plan is fragile under baseline assumptions.",
            "Increasing contributions or delaying retirement would materially improve outcomes."
        ],
        "actions": [
            {
                "action": "Increase annual contributions",
                "reason": "Higher contributions would close the projected gap and improve the Monte Carlo success rate."
            },
            {
                "action": "Consider delaying retirement",
                "reason": "Delaying retirement reduces the withdrawal period and allows more accumulation."
            }
        ],
        "assumption_warnings": [
            "Returns are assumed to follow a lognormal distribution with constant volatility.",
            "Inflation and contribution growth are held constant."
        ],
        "bottom_line": "Your retirement plan carries moderate-to-high risk under current assumptions. The deterministic projection shows a shortfall, and Monte Carlo confirms that market volatility can exhaust the corpus by age 77. Increasing savings, delaying retirement, or reducing planned expenses would meaningfully improve your odds."
    })
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


class TestAIInsightGroqService(unittest.TestCase):
    """Test the Groq AIInsightService directly without HTTP layer."""

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_successful_groq_response(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response()

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)

        self.assertEqual(response.overall_assessment.rating, "moderate")
        self.assertEqual(len(response.risks), 2)
        self.assertEqual(response.risks[0].severity, "high")
        self.assertEqual(len(response.actions), 2)
        self.assertIn("bottom_line", response.model_dump())

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_malformed_groq_response(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.return_value = MagicMock(text="not valid json {{{")

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_api_failure(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.side_effect = Exception("Network error")

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError) as ctx:
            AIInsightService.process_insight_request(request)
        self.assertIn("temporarily unavailable", str(ctx.exception).lower())

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.ai_insights.Groq")
    def test_missing_api_key_raises(self, MockClient):
        with patch.dict(os.environ, {}, clear=True):
            request = AIInsightRequest(**_make_payload())
            with self.assertRaises(ValueError) as ctx:
                AIInsightService.process_insight_request(request)
            self.assertIn("GROQ_API_KEY", str(ctx.exception))

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_validation_failure(self, MockClient):
        mock_client = MockClient.return_value
        invalid_json = json.dumps({
            "overall_assessment": {
                "rating": "invalid_rating",
                "headline": "Test",
                "summary": "Test"
            },
            "deterministic_interpretation": {
                "assessment": "Test",
                "key_points": []
            },
            "monte_carlo_interpretation": {
                "assessment": "Test",
                "key_points": []
            },
            "comparison": {
                "what_deterministic_shows": "Test",
                "what_monte_carlo_adds": "Test",
                "why_the_results_differ": "Test"
            },
            "cash_flow_insights": {
                "pension": "Test",
                "adhoc_expenses": "Test",
                "one_time_retirement_income": "Test",
                "retirement_expenses": "Test"
            },
            "strengths": [],
            "risks": [],
            "key_insights": [],
            "actions": [],
            "assumption_warnings": [],
            "bottom_line": "Test"
        })
        mock_client.chat.completions.create.return_value = MagicMock(text=invalid_json)

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_transient_503_then_success(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.side_effect = [
            APIStatusError(
                message="high demand",
                response=MagicMock(status_code=503),
                body={"error": {"message": "high demand"}}
            ),
            _mock_groq_response(),
        ]

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_all_retries_fail_returns_safe_error(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.side_effect = APIStatusError(
            message="high demand",
            response=MagicMock(status_code=503),
            body={"error": {"message": "high demand"}}
        )

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError) as ctx:
            AIInsightService.process_insight_request(request)
        self.assertIn("temporarily unavailable", str(ctx.exception).lower())
        self.assertEqual(mock_client.chat.completions.create.call_count, 3)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_non_retryable_error_not_retried(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.side_effect = BadRequestError(
            message="bad request",
            response=MagicMock(status_code=400),
            body={"error": {"message": "bad request"}}
        )

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError) as ctx:
            AIInsightService.process_insight_request(request)
        self.assertIn("temporarily unavailable", str(ctx.exception).lower())
        self.assertEqual(mock_client.chat.completions.create.call_count, 1)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_quota_exhausted_429_not_retried(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.side_effect = RateLimitError(
            "Quota exceeded for groq",
            response=MagicMock(status_code=429),
            body={"error": {"message": "Quota exceeded"}}
        )

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)
        self.assertEqual(mock_client.chat.completions.create.call_count, 1)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_transient_429_is_retried(self, MockClient):
        mock_client = MockClient.return_value
        transient_429 = RateLimitError(
            message="rate limit exceeded",
            response=MagicMock(status_code=429),
            body={"error": {"message": "rate limit exceeded"}}
        )
        mock_client.chat.completions.create.side_effect = [
            transient_429,
            _mock_groq_response(),
        ]

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_exception_does_not_expose_internal_details(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.side_effect = APIStatusError(
            message="internal server error",
            response=MagicMock(status_code=500),
            body={"error": {"message": "internal server error"}}
        )

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError) as ctx:
            AIInsightService.process_insight_request(request)
        body = str(ctx.exception)
        self.assertNotIn("internal server error", body.lower())
        self.assertNotIn("stack", body.lower())
        self.assertNotIn("traceback", body.lower())

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_call_groq_uses_json_schema(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response()

        request = AIInsightRequest(**_make_payload())
        AIInsightService.process_insight_request(request)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs["response_format"]["type"], "json_schema")
        self.assertIn("json_schema", call_kwargs["response_format"])
        self.assertEqual(call_kwargs["response_format"]["json_schema"]["name"], "AIInsightResponse")
        self.assertIn("schema", call_kwargs["response_format"]["json_schema"])

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_wrong_schema_repaired_and_accepted(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "deterministic_analysis": {
                "assessment": "Test"
            }
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertIsInstance(response, AIInsightResponse)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_incomplete_response_repaired(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "overall_assessment": {
                "rating": "moderate",
                "headline": "Test",
                "summary": "Test"
            },
            "deterministic_interpretation": {
                "assessment": "Test",
                "key_points": []
            },
            "monte_carlo_interpretation": {
                "assessment": "Test",
                "key_points": []
            },
            "comparison": {
                "what_deterministic_shows": "Test",
                "what_monte_carlo_adds": "Test",
                "why_the_results_differ": "Test"
            },
            "cash_flow_insights": {
                "pension": "Test",
                "adhoc_expenses": "Test",
                "one_time_retirement_income": "Test",
                "retirement_expenses": "Test"
            },
            "strengths": [],
            "risks": [],
            "key_insights": [],
            "actions": []
            # Missing: assumption_warnings, bottom_line
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")
        self.assertEqual(response.assumption_warnings, [])
        self.assertEqual(response.bottom_line, "")

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_empty_response_raises(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = ""
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_malformed_json_raises(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = "not valid json {{{"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_json_array_extracts_first_object(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = json.dumps([
            {"overall_assessment": {"rating": "moderate", "headline": "Test", "summary": "Test"},
             "deterministic_interpretation": {"assessment": "Test", "key_points": []},
             "monte_carlo_interpretation": {"assessment": "Test", "key_points": []},
             "comparison": {"what_deterministic_shows": "Test", "what_monte_carlo_adds": "Test", "why_the_results_differ": "Test"},
             "cash_flow_insights": {"pension": "Test", "adhoc_expenses": "Test", "one_time_retirement_income": "Test", "retirement_expenses": "Test"},
             "strengths": [], "risks": [], "key_insights": [], "actions": [], "assumption_warnings": [], "bottom_line": "Test"}
        ])
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_json_with_code_fences(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = "```json\n" + json.dumps({
            "overall_assessment": {"rating": "moderate", "headline": "Test", "summary": "Test"},
            "deterministic_interpretation": {"assessment": "Test", "key_points": []},
            "monte_carlo_interpretation": {"assessment": "Test", "key_points": []},
            "comparison": {"what_deterministic_shows": "Test", "what_monte_carlo_adds": "Test", "why_the_results_differ": "Test"},
            "cash_flow_insights": {"pension": "Test", "adhoc_expenses": "Test", "one_time_retirement_income": "Test", "retirement_expenses": "Test"},
            "strengths": [], "risks": [], "key_insights": [], "actions": [], "assumption_warnings": [], "bottom_line": "Test"
        }) + "\n```"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_json_with_extra_text_before_and_after(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = "Here is the result: " + json.dumps({
            "overall_assessment": {"rating": "moderate", "headline": "Test", "summary": "Test"},
            "deterministic_interpretation": {"assessment": "Test", "key_points": []},
            "monte_carlo_interpretation": {"assessment": "Test", "key_points": []},
            "comparison": {"what_deterministic_shows": "Test", "what_monte_carlo_adds": "Test", "why_the_results_differ": "Test"},
            "cash_flow_insights": {"pension": "Test", "adhoc_expenses": "Test", "one_time_retirement_income": "Test", "retirement_expenses": "Test"},
            "strengths": [], "risks": [], "key_insights": [], "actions": [], "assumption_warnings": [], "bottom_line": "Test"
        }) + " Hope this helps!"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_json_with_unicode_escapes(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "overall_assessment": {"rating": "moderate", "headline": "Test", "summary": "Test with unicode \u202f and \u2013"},
            "deterministic_interpretation": {"assessment": "Test", "key_points": []},
            "monte_carlo_interpretation": {"assessment": "Test", "key_points": []},
            "comparison": {"what_deterministic_shows": "Test", "what_monte_carlo_adds": "Test", "why_the_results_differ": "Test"},
            "cash_flow_insights": {"pension": "Test", "adhoc_expenses": "Test", "one_time_retirement_income": "Test", "retirement_expenses": "Test"},
            "strengths": [], "risks": [], "key_insights": [], "actions": [], "assumption_warnings": [], "bottom_line": "Test"
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_schema_invalid_response_raises(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "overall_assessment": {
                "rating": "invalid_rating",
                "headline": "Test",
                "summary": "Test"
            },
            "deterministic_interpretation": {
                "assessment": "Test",
                "key_points": []
            },
            "monte_carlo_interpretation": {
                "assessment": "Test",
                "key_points": []
            },
            "comparison": {
                "what_deterministic_shows": "Test",
                "what_monte_carlo_adds": "Test",
                "why_the_results_differ": "Test"
            },
            "cash_flow_insights": {
                "pension": "Test",
                "adhoc_expenses": "Test",
                "one_time_retirement_income": "Test",
                "retirement_expenses": "Test"
            },
            "strengths": [],
            "risks": [],
            "key_insights": [],
            "actions": [],
            "assumption_warnings": [],
            "bottom_line": "Test"
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_json_null_raises(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = "null"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_json_string_raises(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = '"just a string"'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_json_number_raises(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = "42"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_empty_object_repaired(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = "{}"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")
        self.assertEqual(response.bottom_line, "")

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_413_tpm_not_retried(self, MockClient):
        mock_client = MockClient.return_value
        tpm_413 = APIStatusError(
            message="Request too large for model on tokens per minute (TPM): Limit 8000, Requested 8862",
            response=MagicMock(status_code=413),
            body={"error": {"message": "Request too large", "code": "rate_limit_exceeded"}}
        )
        mock_client.chat.completions.create.side_effect = tpm_413

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)
        self.assertEqual(mock_client.chat.completions.create.call_count, 1)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_413_non_tpm_not_retried(self, MockClient):
        mock_client = MockClient.return_value
        non_tpm_413 = APIStatusError(
            message="Request too large for some other reason",
            response=MagicMock(status_code=413),
            body={"error": {"message": "Request too large"}}
        )
        mock_client.chat.completions.create.side_effect = non_tpm_413

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)
        self.assertEqual(mock_client.chat.completions.create.call_count, 1)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_compact_prompt_contains_required_fields(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response()

        request = AIInsightRequest(**_make_payload())
        AIInsightService.process_insight_request(request)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        prompt = call_kwargs["messages"][1]["content"]
        parsed = json.loads(prompt)

        self.assertIn("user_inputs", parsed)
        self.assertIn("predictive_analysis", parsed)
        self.assertIn("monte_carlo_analysis", parsed)
        self.assertIn("methodology", parsed)

        self.assertIn("current_age", parsed["user_inputs"])
        self.assertIn("retirement_age", parsed["user_inputs"])
        self.assertIn("life_expectancy", parsed["user_inputs"])
        self.assertIn("current_annual_expenses", parsed["user_inputs"])
        self.assertIn("avg_inflation_rate", parsed["user_inputs"])
        self.assertIn("current_corpus", parsed["user_inputs"])
        self.assertIn("annual_contribution", parsed["user_inputs"])
        self.assertIn("pre_retirement_return", parsed["user_inputs"])
        self.assertIn("post_retirement_return", parsed["user_inputs"])
        self.assertIn("allocation_equity", parsed["user_inputs"])
        self.assertIn("allocation_debt", parsed["user_inputs"])
        self.assertIn("allocation_arbitrage", parsed["user_inputs"])
        self.assertIn("include_pension", parsed["user_inputs"])
        self.assertIn("adhoc_expenses", parsed["user_inputs"])
        self.assertIn("volatility_equity", parsed["user_inputs"])
        self.assertIn("equity_debt_correlation", parsed["user_inputs"])

        self.assertIn("success_rate", parsed["monte_carlo_analysis"])
        self.assertIn("median_final_corpus", parsed["monte_carlo_analysis"])
        self.assertIn("existing_recommendations", parsed["monte_carlo_analysis"])
        self.assertIn("retirement_age_sensitivity", parsed["monte_carlo_analysis"])

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_compact_prompt_excludes_large_structures(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response()

        request = AIInsightRequest(**_make_payload())
        AIInsightService.process_insight_request(request)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        prompt = call_kwargs["messages"][1]["content"]
        parsed = json.loads(prompt)

        self.assertNotIn("final_corpus_histogram", parsed["monte_carlo_analysis"])
        self.assertNotIn("yearly_percentiles", parsed.get("user_inputs", {}))
        self.assertNotIn("monte_carlo_seed", parsed["user_inputs"])

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_compact_prompt_preserves_numerical_recommendations(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response()

        payload = _make_payload()
        payload["monte_carlo_analysis"]["existing_recommendations"] = [
            "Increase contribution by ₹50,000 per year",
            "Delay retirement by 2 years"
        ]
        payload["monte_carlo_analysis"]["retirement_age_sensitivity"] = {
            "52": {"success_rate": 45.2},
            "56": {"success_rate": 78.1}
        }
        request = AIInsightRequest(**payload)
        AIInsightService.process_insight_request(request)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        prompt = call_kwargs["messages"][1]["content"]
        parsed = json.loads(prompt)

        self.assertEqual(
            parsed["monte_carlo_analysis"]["existing_recommendations"],
            ["Increase contribution by ₹50,000 per year", "Delay retirement by 2 years"]
        )
        self.assertEqual(
            parsed["monte_carlo_analysis"]["retirement_age_sensitivity"],
            {"52": {"success_rate": 45.2}, "56": {"success_rate": 78.1}}
        )

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_compact_prompt_validation_still_enforced(self, MockClient):
        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "overall_assessment": {"rating": "moderate", "headline": "Test", "summary": "Test"},
            "deterministic_interpretation": {"assessment": "Test", "key_points": []},
            "monte_carlo_interpretation": {"assessment": "Test", "key_points": []},
            "comparison": {"what_deterministic_shows": "Test", "what_monte_carlo_adds": "Test", "why_the_results_differ": "Test"},
            "cash_flow_insights": {"pension": "Test", "adhoc_expenses": "Test", "one_time_retirement_income": "Test", "retirement_expenses": "Test"},
            "strengths": [], "risks": [], "key_insights": [], "actions": [], "assumption_warnings": [], "bottom_line": "Test"
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertIsInstance(response, AIInsightResponse)
        self.assertEqual(response.overall_assessment.rating, "moderate")


class TestAIInsightGeminiService(unittest.TestCase):
    """Test the Gemini AIInsightService directly without HTTP layer."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_successful_gemini_response(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.models.generate_content.return_value = _mock_gemini_response()

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)

        self.assertEqual(response.overall_assessment.rating, "moderate")
        self.assertEqual(len(response.risks), 2)
        self.assertEqual(response.risks[0].severity, "high")
        self.assertEqual(len(response.actions), 2)
        self.assertIn("bottom_line", response.model_dump())

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_malformed_gemini_response(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.models.generate_content.return_value = MagicMock(text="not valid json {{{")

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_gemini_api_failure(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.models.generate_content.side_effect = Exception("Network error")

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError) as ctx:
            AIInsightService.process_insight_request(request)
        self.assertIn("temporarily unavailable", str(ctx.exception).lower())

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_missing_gemini_api_key_raises(self, MockClient):
        with patch.dict(os.environ, {}, clear=True):
            request = AIInsightRequest(**_make_payload())
            with self.assertRaises(ValueError) as ctx:
                AIInsightService.process_insight_request(request)
            self.assertIn("GROQ_API_KEY", str(ctx.exception))

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_gemini_validation_failure(self, MockClient):
        mock_client = MockClient.return_value
        invalid_json = json.dumps({
            "overall_assessment": {
                "rating": "invalid_rating",
                "headline": "Test",
                "summary": "Test"
            },
            "deterministic_interpretation": {
                "assessment": "Test",
                "key_points": []
            },
            "monte_carlo_interpretation": {
                "assessment": "Test",
                "key_points": []
            },
            "comparison": {
                "what_deterministic_shows": "Test",
                "what_monte_carlo_adds": "Test",
                "why_the_results_differ": "Test"
            },
            "cash_flow_insights": {
                "pension": "Test",
                "adhoc_expenses": "Test",
                "one_time_retirement_income": "Test",
                "retirement_expenses": "Test"
            },
            "strengths": [],
            "risks": [],
            "key_insights": [],
            "actions": [],
            "assumption_warnings": [],
            "bottom_line": "Test"
        })
        mock_client.models.generate_content.return_value = MagicMock(text=invalid_json)

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_transient_503_then_success(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.models.generate_content.side_effect = [
            genai.errors.ServerError(503, {"error": {"message": "high demand"}}, None),
            _mock_gemini_response(),
        ]

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_all_retries_fail_returns_safe_error(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.models.generate_content.side_effect = genai.errors.ServerError(
            503, {"error": {"message": "high demand"}}, None
        )

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError) as ctx:
            AIInsightService.process_insight_request(request)
        self.assertIn("temporarily unavailable", str(ctx.exception).lower())
        self.assertEqual(mock_client.models.generate_content.call_count, 3)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_non_retryable_error_not_retried(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.models.generate_content.side_effect = genai.errors.ClientError(
            400, {"error": {"message": "bad request"}}, None
        )

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError) as ctx:
            AIInsightService.process_insight_request(request)
        self.assertIn("temporarily unavailable", str(ctx.exception).lower())
        self.assertEqual(mock_client.models.generate_content.call_count, 1)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_quota_exhausted_429_not_retried(self, MockClient):
        mock_client = MockClient.return_value
        mock_response = MagicMock()
        mock_response.status = "RESOURCE_EXHAUSTED"
        mock_client.models.generate_content.side_effect = genai.errors.ClientError(
            429,
            {"error": {"message": "Quota exceeded", "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure"}]}},
            mock_response,
        )

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError):
            AIInsightService.process_insight_request(request)
        self.assertEqual(mock_client.models.generate_content.call_count, 1)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_transient_429_is_retried(self, MockClient):
        mock_client = MockClient.return_value
        transient_429 = genai.errors.ClientError(
            429, {"error": {"message": "rate limit exceeded"}}, None
        )
        mock_client.models.generate_content.side_effect = [
            transient_429,
            _mock_gemini_response(),
        ]

        request = AIInsightRequest(**_make_payload())
        response = AIInsightService.process_insight_request(request)
        self.assertEqual(response.overall_assessment.rating, "moderate")
        self.assertEqual(mock_client.models.generate_content.call_count, 2)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True)
    @patch("src.ai_insights.genai.Client")
    def test_gemini_exception_does_not_expose_internal_details(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.models.generate_content.side_effect = genai.errors.ServerError(
            500, {"error": {"message": "internal server error"}}, None
        )

        request = AIInsightRequest(**_make_payload())
        with self.assertRaises(RuntimeError) as ctx:
            AIInsightService.process_insight_request(request)
        body = str(ctx.exception)
        self.assertNotIn("internal server error", body.lower())
        self.assertNotIn("stack", body.lower())
        self.assertNotIn("traceback", body.lower())


class TestAIInsightEndpoint(unittest.TestCase):
    """Test the /api/ai-insight HTTP endpoint."""

    def setUp(self):
        from src.main import get_client_ip
        from slowapi import Limiter

        self.test_app = FastAPI()
        self.test_limiter = Limiter(key_func=get_client_ip)
        self.test_app.state.limiter = self.test_limiter
        self.test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        @self.test_app.post("/api/ai-insight")
        @self.test_limiter.limit("100/minute")
        def ai_insight(request: Request, payload: AIInsightRequest):
            try:
                return AIInsightService.process_insight_request(payload)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except RuntimeError as e:
                raise HTTPException(status_code=502, detail=str(e))
            except Exception:
                raise HTTPException(status_code=500, detail="The AI service is temporarily unavailable. Please try again later.")

        self.client = TestClient(self.test_app, raise_server_exceptions=False)
        self.payload = _make_payload()

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_successful_groq_response(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response()

        response = self.client.post("/api/ai-insight", json=self.payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["overall_assessment"]["rating"], "moderate")
        self.assertEqual(len(data["risks"]), 2)
        self.assertEqual(data["risks"][0]["severity"], "high")
        self.assertEqual(len(data["actions"]), 2)
        self.assertIn("bottom_line", data)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_api_failure(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.side_effect = Exception("Network error")

        response = self.client.post("/api/ai-insight", json=self.payload)
        self.assertEqual(response.status_code, 502)
        self.assertIn("temporarily unavailable", response.json()["detail"].lower())

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.ai_insights.Groq")
    def test_missing_api_key_raises(self, MockClient):
        response = self.client.post("/api/ai-insight", json=self.payload)
        self.assertEqual(response.status_code, 400)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_groq_exception_does_not_expose_internal_details(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.side_effect = APIStatusError(
            message="internal server error",
            response=MagicMock(status_code=500),
            body={"error": {"message": "internal server error"}}
        )

        response = self.client.post("/api/ai-insight", json=self.payload)
        self.assertEqual(response.status_code, 502)
        body = response.json()["detail"]
        self.assertNotIn("internal server error", body.lower())
        self.assertNotIn("stack", body.lower())
        self.assertNotIn("traceback", body.lower())


class TestAIInsightRateLimiting(unittest.TestCase):
    """Test rate limiting behavior."""

    def setUp(self):
        from src.main import get_client_ip
        from slowapi import Limiter

        self.test_app = FastAPI()
        self.test_limiter = Limiter(key_func=get_client_ip)
        self.test_app.state.limiter = self.test_limiter
        self.test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        @self.test_app.post("/api/ai-insight")
        @self.test_limiter.limit("5/minute")
        def ai_insight(request: Request, payload: AIInsightRequest):
            return AIInsightService.process_insight_request(payload)

        self.client = TestClient(self.test_app, raise_server_exceptions=False)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "openai/gpt-oss-120b"})
    @patch("src.ai_insights.Groq")
    def test_rate_limiting_blocks_after_max_requests(self, MockClient):
        mock_client = MockClient.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response()
        payload = _make_payload()

        for i in range(5):
            response = self.client.post("/api/ai-insight", json=payload)
            self.assertEqual(response.status_code, 200, f"Request {i+1} should succeed")

        response = self.client.post("/api/ai-insight", json=payload)
        self.assertEqual(response.status_code, 429)
        self.assertIn("5 per 1 minute", str(response.json()))


class TestAIInsightProviderConfig(unittest.TestCase):
    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                _get_provider_config()
            self.assertIn("GROQ_API_KEY", str(ctx.exception))

    def test_groq_preferred_when_both_keys_set(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "groq-key", "GEMINI_API_KEY": "gemini-key"}, clear=True):
            api_key, model, provider = _get_provider_config()
            self.assertEqual(api_key, "groq-key")
            self.assertEqual(provider, "groq")

    def test_gemini_used_when_only_gemini_key_set(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-key", "GEMINI_MODEL": "gemini-3.6-flash"}, clear=True):
            api_key, model, provider = _get_provider_config()
            self.assertEqual(api_key, "gemini-key")
            self.assertEqual(provider, "gemini")

    def test_groq_custom_model(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "custom-model"}, clear=True):
            api_key, model, provider = _get_provider_config()
            self.assertEqual(api_key, "test-key")
            self.assertEqual(model, "custom-model")
            self.assertEqual(provider, "groq")

    def test_groq_default_model_when_not_set(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=True):
            api_key, model, provider = _get_provider_config()
            self.assertEqual(api_key, "test-key")
            self.assertEqual(model, "openai/gpt-oss-120b")
            self.assertEqual(provider, "groq")

    def test_gemini_default_model_when_not_set(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            api_key, model, provider = _get_provider_config()
            self.assertEqual(api_key, "test-key")
            self.assertEqual(model, "gemini-3.6-flash")
            self.assertEqual(provider, "gemini")


class TestAIInsightGeminiConfig(unittest.TestCase):
    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                _get_gemini_config()
            self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    def test_custom_model(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "custom-model"}, clear=True):
            api_key, model = _get_gemini_config()
            self.assertEqual(api_key, "test-key")
            self.assertEqual(model, "custom-model")

    def test_default_model_when_not_set(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            api_key, model = _get_gemini_config()
            self.assertEqual(api_key, "test-key")
            self.assertEqual(model, "gemini-3.6-flash")


class TestExtractJson(unittest.TestCase):
    def test_plain_json(self):
        raw = '{"key": "value"}'
        self.assertEqual(_extract_json_from_text(raw), {"key": "value"})

    def test_markdown_code_block(self):
        raw = '```json\n{"key": "value"}\n```'
        self.assertEqual(_extract_json_from_text(raw), {"key": "value"})

    def test_markdown_no_language(self):
        raw = '```\n{"key": "value"}\n```'
        self.assertEqual(_extract_json_from_text(raw), {"key": "value"})

    def test_json_with_extra_text(self):
        raw = 'Here is the result: {"key": "value"} Hope this helps!'
        self.assertEqual(_extract_json_from_text(raw), {"key": "value"})

    def test_json_with_trailing_text_and_braces(self):
        raw = '{"key": "value"} Additional explanation {with braces}'
        self.assertEqual(_extract_json_from_text(raw), {"key": "value"})


class TestCompactPrompt(unittest.TestCase):
    def test_compact_funding_probability_under_threshold(self):
        fp = {str(age): float(age) for age in range(58, 91)}
        compact = _compact_funding_probability(fp)
        self.assertLessEqual(len(compact), 12)
        self.assertIn("58", compact)
        self.assertIn("90", compact)

    def test_compact_funding_probability_small_input(self):
        fp = {"60": 80.0, "65": 65.0, "70": 50.0}
        compact = _compact_funding_probability(fp)
        self.assertEqual(compact, fp)

    def test_compact_funding_probability_empty(self):
        compact = _compact_funding_probability({})
        self.assertEqual(compact, {})

    def test_build_compact_prompt_structure(self):
        request = AIInsightRequest(**_make_payload())
        prompt = _build_compact_prompt(request)
        parsed = json.loads(prompt)

        self.assertIn("user_inputs", parsed)
        self.assertIn("predictive_analysis", parsed)
        self.assertIn("monte_carlo_analysis", parsed)
        self.assertIn("methodology", parsed)

    def test_build_compact_prompt_excludes_large_structures(self):
        request = AIInsightRequest(**_make_payload())
        prompt = _build_compact_prompt(request)
        parsed = json.loads(prompt)

        self.assertNotIn("final_corpus_histogram", parsed["monte_carlo_analysis"])
        self.assertNotIn("yearly_percentiles", parsed.get("user_inputs", {}))
        self.assertNotIn("monte_carlo_seed", parsed["user_inputs"])

    def test_build_compact_prompt_preserves_recommendations(self):
        payload = _make_payload()
        payload["monte_carlo_analysis"]["existing_recommendations"] = [
            "Increase contribution by ₹50,000 per year",
            "Delay retirement by 2 years"
        ]
        payload["monte_carlo_analysis"]["retirement_age_sensitivity"] = {
            "52": {"success_rate": 45.2},
            "56": {"success_rate": 78.1}
        }
        request = AIInsightRequest(**payload)
        prompt = _build_compact_prompt(request)
        parsed = json.loads(prompt)

        self.assertEqual(
            parsed["monte_carlo_analysis"]["existing_recommendations"],
            ["Increase contribution by ₹50,000 per year", "Delay retirement by 2 years"]
        )
        self.assertEqual(
            parsed["monte_carlo_analysis"]["retirement_age_sensitivity"],
            {"52": {"success_rate": 45.2}, "56": {"success_rate": 78.1}}
        )

    def test_build_compact_prompt_funding_probability_compacted(self):
        payload = _make_payload()
        fp = {str(age): 100.0 - age for age in range(58, 91)}
        payload["monte_carlo_analysis"]["funding_probability_by_age"] = fp
        request = AIInsightRequest(**payload)
        prompt = _build_compact_prompt(request)
        parsed = json.loads(prompt)

        compact_fp = parsed["monte_carlo_analysis"]["funding_probability_by_age"]
        self.assertLessEqual(len(compact_fp), 12)
        self.assertIn("58", compact_fp)
        self.assertIn("90", compact_fp)


class TestAIInsightModels(unittest.TestCase):
    def test_predictive_summary_valid(self):
        summary = PredictiveAnalysisSummary(
            readiness_percent=95.18,
            plan_sustainable=False,
            corpus_at_retirement=152960169.0,
            minimum_corpus_required=160709753.0,
            gap_at_retirement=7749583.0,
            years_in_retirement=25,
            corpus_exhaustion_age=None,
            total_contributions=25000000.0,
            total_pension_received=0.0,
            average_pension_coverage=0.0,
            required_pre_retirement_return=10.32,
            required_post_retirement_return=8.47
        )
        self.assertEqual(summary.readiness_percent, 95.18)
        self.assertFalse(summary.plan_sustainable)

    def test_monte_carlo_summary_valid(self):
        summary = MonteCarloAnalysisSummary(
            success_rate=33.0,
            median_final_corpus=0.0,
            mean_final_corpus=50000000.0,
            std_final_corpus=150000000.0,
            p5_final_corpus=0.0,
            p95_final_corpus=468095519.0,
            failure_age_percentiles={"p50": 77, "p75": 80},
            funding_probability_by_age={"60": 100.0, "65": 85.0},
            final_corpus_histogram={"labels": ["A", "B"], "probabilities": [45.0, 20.0]},
            num_simulations=100,
            retirement_age_sensitivity={"58": {"success_rate": 28.0}},
            existing_recommendations=["Rec 1"]
        )
        self.assertEqual(summary.success_rate, 33.0)
        self.assertEqual(summary.num_simulations, 100)
        self.assertEqual(len(summary.existing_recommendations), 1)

    def test_methodology_context_valid(self):
        context = MethodologyContext(
            success_definition="Success means funding all expenses.",
            failure_definition="Failure means corpus reaches zero.",
            percentile_explanation="p5 is exceeded by 95% of paths.",
            funding_probability_explanation="Probability of fully funded expenses in a given year.",
            recommended_success_threshold="Target 80-90%."
        )
        self.assertEqual(context.success_definition, "Success means funding all expenses.")

    def test_ai_insight_response_model(self):
        response = AIInsightResponse(
            overall_assessment=OverallAssessment(
                rating="moderate",
                headline="Test headline",
                summary="Test summary"
            ),
            deterministic_interpretation=DeterministicInterpretation(
                assessment="Test assessment",
                key_points=["Point 1"]
            ),
            monte_carlo_interpretation=MonteCarloInterpretation(
                assessment="Test MC",
                key_points=["MC point 1"]
            ),
            comparison=Comparison(
                what_deterministic_shows="Deterministic shows",
                what_monte_carlo_adds="MC adds",
                why_the_results_differ="They differ"
            ),
            cash_flow_insights=CashFlowInsights(
                pension="Pension insight",
                adhoc_expenses="Ad-hoc insight",
                one_time_retirement_income="Income insight",
                retirement_expenses="Expense insight"
            ),
            strengths=["Strength 1"],
            risks=[RiskItem(severity="high", risk="Risk 1", explanation="Explanation 1")],
            key_insights=["Insight 1"],
            actions=[ActionItem(action="Action 1", reason="Reason 1")],
            assumption_warnings=["Warning 1"],
            bottom_line="Bottom line text."
        )
        self.assertEqual(response.overall_assessment.rating, "moderate")
        self.assertEqual(len(response.risks), 1)
        self.assertEqual(response.risks[0].severity, "high")

    def test_references_to_existing_facts_accepted(self):
        request = AIInsightRequest(**_make_payload())
        response = AIInsightResponse(
            overall_assessment=OverallAssessment(rating="moderate", headline="Test", summary="Test"),
            deterministic_interpretation=DeterministicInterpretation(assessment="Test", key_points=[]),
            monte_carlo_interpretation=MonteCarloInterpretation(assessment="Test", key_points=[]),
            comparison=Comparison(what_deterministic_shows="Test", what_monte_carlo_adds="Test", why_the_results_differ="Test"),
            cash_flow_insights=CashFlowInsights(pension="Test", adhoc_expenses="Test", one_time_retirement_income="Test", retirement_expenses="Test"),
            strengths=[],
            risks=[],
            key_insights=[],
            actions=[
                ActionItem(
                    action="Target the recommended 80-90% success threshold",
                    reason="The methodology recommends 80-90% for moderate risk tolerance."
                ),
                ActionItem(
                    action="Use the 23-year accumulation period",
                    reason="The model projects 23 years from age 35 to 58."
                ),
                ActionItem(
                    action="Retire at age 58",
                    reason="This matches the current user input."
                )
            ],
            assumption_warnings=[],
            bottom_line="Test"
        )
        from src.ai_insights import _validate_numerical_recommendations
        _validate_numerical_recommendations(response, request)

    def test_invented_quantitative_recommendation_rejected(self):
        request = AIInsightRequest(**_make_payload())
        response = AIInsightResponse(
            overall_assessment=OverallAssessment(rating="moderate", headline="Test", summary="Test"),
            deterministic_interpretation=DeterministicInterpretation(assessment="Test", key_points=[]),
            monte_carlo_interpretation=MonteCarloInterpretation(assessment="Test", key_points=[]),
            comparison=Comparison(what_deterministic_shows="Test", what_monte_carlo_adds="Test", why_the_results_differ="Test"),
            cash_flow_insights=CashFlowInsights(pension="Test", adhoc_expenses="Test", one_time_retirement_income="Test", retirement_expenses="Test"),
            strengths=[],
            risks=[],
            key_insights=[],
            actions=[
                ActionItem(
                    action="Increase contributions by 20%",
                    reason="This would close the gap."
                ),
                ActionItem(
                    action="Save an additional ₹200000 per year",
                    reason="This would improve outcomes."
                ),
                ActionItem(
                    action="Delay retirement by 3 years",
                    reason="This reduces withdrawal pressure."
                )
            ],
            assumption_warnings=[],
            bottom_line="Test"
        )
        from src.ai_insights import _validate_numerical_recommendations
        with self.assertRaises(ValueError):
            _validate_numerical_recommendations(response, request)

    def test_engine_supplied_recommendation_accepted(self):
        request = AIInsightRequest(**_make_payload())
        request.monte_carlo_analysis.existing_recommendations = ["Save an additional ₹182000 per year."]
        response = AIInsightResponse(
            overall_assessment=OverallAssessment(rating="moderate", headline="Test", summary="Test"),
            deterministic_interpretation=DeterministicInterpretation(assessment="Test", key_points=[]),
            monte_carlo_interpretation=MonteCarloInterpretation(assessment="Test", key_points=[]),
            comparison=Comparison(what_deterministic_shows="Test", what_monte_carlo_adds="Test", why_the_results_differ="Test"),
            cash_flow_insights=CashFlowInsights(pension="Test", adhoc_expenses="Test", one_time_retirement_income="Test", retirement_expenses="Test"),
            strengths=[],
            risks=[],
            key_insights=[],
            actions=[
                ActionItem(
                    action="Save an additional ₹182000 per year",
                    reason="This matches the engine recommendation."
                )
            ],
            assumption_warnings=[],
            bottom_line="Test"
        )
        from src.ai_insights import _validate_numerical_recommendations
        _validate_numerical_recommendations(response, request)

    def test_mixed_legitimate_and_invented_numbers_rejected(self):
        request = AIInsightRequest(**_make_payload())
        response = AIInsightResponse(
            overall_assessment=OverallAssessment(rating="moderate", headline="Test", summary="Test"),
            deterministic_interpretation=DeterministicInterpretation(assessment="Test", key_points=[]),
            monte_carlo_interpretation=MonteCarloInterpretation(assessment="Test", key_points=[]),
            comparison=Comparison(what_deterministic_shows="Test", what_monte_carlo_adds="Test", why_the_results_differ="Test"),
            cash_flow_insights=CashFlowInsights(pension="Test", adhoc_expenses="Test", one_time_retirement_income="Test", retirement_expenses="Test"),
            strengths=[],
            risks=[],
            key_insights=[],
            actions=[
                ActionItem(
                    action="Retire at age 58 and increase contributions by 20%",
                    reason="Age 58 is your current input, but 20% is not engine-supplied."
                )
            ],
            assumption_warnings=[],
            bottom_line="Test"
        )
        from src.ai_insights import _validate_numerical_recommendations
        with self.assertRaises(ValueError):
            _validate_numerical_recommendations(response, request)


if __name__ == "__main__":
    unittest.main()
