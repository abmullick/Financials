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
| `num_simulations` | 1,000 | 100–50,000 | Number of paths simulated per run |
| `return_distribution` | Lognormal | Normal / Lognormal | Distribution used for annual returns |
| `volatility_equity` | 18.0% | 0–100% | Annual std dev of equity returns |
| `volatility_debt` | 6.0% | 0–100% | Annual std dev of debt returns |
| `volatility_arbitrage` | 8.0% | 0–100% | Annual std dev of arbitrage returns |
| `monte_carlo_seed` | None | Any integer | Optional seed for reproducible results |

### How Volatility Is Applied

Each year's return volatility is a weighted blend of the three asset classes based on your portfolio allocation:

```
portfolio_volatility = (equity% × equity_volatility) +
                        (debt% × debt_volatility) +
                        (arbitrage% × arbitrage_volatility)
```

This applies during **both** accumulation and retirement phases.

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

## Running Tests

```bash
source ~/spark_venv/bin/activate
PYTHONPATH=/home/abmul/projects/financials/retirals/src python3 -m unittest tests.test_retirement -v
```

## Architecture

- **Backend**: FastAPI (`src/main.py`) with Pydantic validation (`src/models.py`)
- **Engine**: Deterministic projection + Monte Carlo simulation (`src/retirement_engine.py`)
- **Frontend**: Single-page HTML/JS app (`src/static/index.html`) with Chart.js for visualization
