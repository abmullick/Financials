# Parity Retirement Planner

A web-based retirement planning tool that combines deterministic projection with Monte Carlo simulation to estimate retirement readiness and corpus sustainability.

## Features

- **Deterministic Projection** — Year-by-year retirement ledger with corpus, contributions, withdrawals, taxes, and ad-hoc expenses.
- **Monte Carlo Simulation** — Probabilistic analysis using stochastic returns to estimate success rates and percentile bands.
- **Stress Testing** — Optional mild/severe market crashes in the first two years of retirement.
- **Pension Modeling** — Gross/net pension with tax, surplus reinvestment, and expense coverage.
- **Goal-Seek & Advisory** — Required return analysis and retirement readiness scoring.
- **Dark/Light Theme** — Persistent theme with responsive charts and collapsible sections.
- **Report Export** — Download results as PDF or HTML.
- **AI Insights** — AI-powered interpretation of deterministic and Monte Carlo results, with evidence-based actions and risk analysis.

## Quick Start

```bash
source ~/spark_venv/bin/activate
uvicorn src.main:app --reload
```

Open `http://localhost:20080/` in your browser.

## Monte Carlo Methodology

### What It Does

Monte Carlo simulation runs thousands of hypothetical market paths to answer: **"What are the chances my retirement plan will work?"**

Unlike the deterministic projection, which assumes average returns every year, Monte Carlo draws random returns from a probability distribution to capture real-world uncertainty.

### Parameters

| Parameter | Default | Range | Description |
|---|---|---|---|
| `num_simulations` | 1,000 | 1,000 / 2,000 / 5,000 / 10,000 / 20,000 | Number of paths simulated per run |
| `return_distribution` | Lognormal | Normal / Lognormal | Distribution used for annual returns |
| `volatility_equity` | 18.0% | 0–100% | Annual std dev of equity returns |
| `volatility_debt` | 6.0% | 0–100% | Annual std dev of debt returns |
| `volatility_arbitrage` | 8.0% | 0–100% | Annual std dev of arbitrage returns |
| `equity_debt_correlation` | -0.10 | -1 to +1 | Correlation between equity and debt returns |
| `equity_arbitrage_correlation` | 0.05 | -1 to +1 | Correlation between equity and arbitrage returns |
| `debt_arbitrage_correlation` | 0.20 | -1 to +1 | Correlation between debt and arbitrage returns |
| `monte_carlo_seed` | None | Any integer | Optional seed for reproducible results |
| `retirement_age_sensitivity` | None | Comma-separated ages | Optional list of retirement ages to compare success rates |

### Outputs

| Metric | Description |
|---|---|
| **Probability of Success** | % of simulated paths where the corpus never exhausts. |
| **Median Final Corpus** | The middle outcome across all paths. |
| **5th / 25th / 75th / 95th Percentiles** | Distribution bands showing worst, below-average, above-average, and best outcomes. |
| **Funding Probability by Age** | For each age, the % of simulations where expenses are fully funded. |
| **Failure Age Percentiles** | For failed paths, the ages at which corpus first exhausts (10th, 25th, 50th, 75th, 90th percentiles). |
| **Final Corpus Histogram** | 20-bin histogram of final corpus values across all simulations. |
| **Retirement Age Sensitivity** | Success rates and median corpus for alternative retirement ages. |
| **Recommendations** | Plain-language suggestions based on MC output. |

### How Volatility Is Applied

```
variance =
    we² × σe²
  + wd² × σd²
  + wa² × σa²
  + 2 × we × wd × σe × σd × ρed
  + 2 × we × wa × σe × σa × ρea
  + 2 × wd × wa × σd × σa × ρda

portfolio_volatility = sqrt(max(variance, 0))
```

Where:
- `we`, `wd`, `wa` = equity, debt, arbitrage weights
- `σe`, `σd`, `σa` = equity, debt, arbitrage volatilities
- `ρed`, `ρea`, `ρda` = correlations between each pair

This applies during **both** accumulation and retirement phases. Diversification benefits are captured when correlations are less than +1, and risk is amplified when correlations are positive.

### Return Distributions

**Lognormal (default, recommended)**
- Models asset prices correctly.
- Cannot produce returns below -100%.
- Industry standard for retirement planning.

**Normal**
- Simpler distribution.
- Can theoretically produce returns below -100%, implying negative portfolio values.
- Less realistic for long horizons; included mainly for comparison.

### Stress Scenarios

For the first two years of retirement, you can override random returns with a deterministic crash:
- **Mild Crash**: -10% annual return for 2 years
- **Severe Crash**: -20% annual return for 2 years

### Pension Integration

Pension is applied every year from `pension_start_age` onward:
- Gross pension is reduced by tax to get net pension.
- Net pension first covers living expenses.
- Any surplus is reinvested into the corpus.
- Any shortfall must come from portfolio withdrawals.

Pension always reduces corpus pressure and improves the probability of success.

### Failure Criteria

A simulation path is marked as a **failure** if, during retirement, the corpus exhausts while there are still unfunded expenses. Once a path fails, its corpus is held at zero for the remaining years.

### Outputs

| Metric | Description |
|---|---|
| **Probability of Success** | % of simulated paths where the corpus never exhausts. |
| **Median Final Corpus** | The middle outcome across all paths. |
| **5th / 25th / 75th / 95th Percentiles** | Distribution bands showing worst, below-average, above-average, and best outcomes. |

### Practical Notes

- **Seed**: Use a seed to reproduce exact results across runs. The same inputs + seed always produce identical outputs. Seeds have no inherent meaning (e.g., `42` is not "the 1987 crash").
- **Simulation Count**: More simulations produce more stable percentiles but take longer. 1,000–5,000 is usually sufficient.
- **Lognormal vs. Normal**: Lognormal is strongly recommended for long retirement horizons.

## API Endpoints

| Method | Path | Rate Limit | Description |
|---|---|---|---|
| `POST` | `/calculate` | 10/min | Deterministic retirement projection |
| `POST` | `/calculate-mc` | 5/min | Monte Carlo simulation |
| `POST` | `/api/ai-insight` | 5/min | AI-powered retirement insight generation |

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes* | Groq API key for AI Insights |
| `GROQ_MODEL` | No | Groq model name (default: `openai/gpt-oss-120b`) |
| `GEMINI_API_KEY` | Yes* | Google Gemini API key for AI Insights (alternative to Groq) |
| `GEMINI_MODEL` | No | Gemini model name (default: `gemini-3.6-flash`) |

\* Either `GROQ_API_KEY` or `GEMINI_API_KEY` must be set. Groq is preferred when both are present.

## Running Tests

```bash
source ~/spark_venv/bin/activate
PYTHONPATH=/home/abmul/projects/financials/retirals/src python3 -m unittest tests.test_retirement -v
```

## Architecture

- **Backend**: FastAPI (`src/main.py`) with Pydantic validation (`src/models.py`)
- **Engine**: Deterministic projection + Monte Carlo simulation (`src/retirement_engine.py`)
- **AI Insights**: AI-powered analysis service (`src/ai_insights.py`) with provider abstraction (Groq or Gemini)
- **Frontend**: Single-page HTML/JS app (`src/static/index.html`) with Chart.js for visualization
- **AI Insights Page**: Separate results page (`src/static/ai-insights.html`) for AI-generated analysis
