# Monte Carlo Simulation — Retirement Planner

## What is Monte Carlo?

Monte Carlo simulation is a technique that answers the question: **"What are the chances my retirement plan will work?"**

Instead of giving you one single projection (like the deterministic "Retirement Readiness" calculation), Monte Carlo runs thousands of hypothetical futures and tells you how often you end up with enough money.

Think of it like this:
- **Deterministic projection** = "Here is what happens if markets deliver average returns."
- **Monte Carlo** = "Here is what happens across 10,000 different possible market paths — good, bad, and ugly."

## Why We Use It for Retirement

Retirement planning spans 30–40 years. Over that period, markets will experience many up years and down years. A single average-return projection hides the risk that a string of bad years early in retirement can permanently damage your corpus.

Monte Carlo makes that risk visible by showing the full distribution of outcomes, not just the average.

## The Theory in Plain English

### 1. Returns Are Uncertain

We don't know next year's market return. But based on history, we know:
- Equity tends to return about 8–12% per year on average, with a standard deviation around 18%
- Debt tends to return about 6–8% per year, with lower volatility around 6%
- Arbitrage tends to sit in between

"Standard deviation" is just a measure of how much returns bounce around. Higher standard deviation = more uncertainty.

### 2. Simulating the Future

For each year of your plan, the simulation draws a random return from a probability distribution. Over thousands of simulations, this builds up a realistic spread of possible futures.

We support two distributions:

**Lognormal (default, recommended)**
- The standard choice for modeling asset prices.
- It cannot produce returns below -100%, which is physically correct — you cannot lose more than 100% of your money.
- This is the industry-standard assumption for retirement planning.

**Normal**
- Simpler, but can theoretically produce returns below -100%, implying a negative portfolio value.
- Mathematically convenient but less realistic for long horizons.

### 3. Portfolio Blending

Your money is split across equity, debt, and arbitrage. Each year's portfolio volatility is calculated using a **covariance-based formula** that accounts for the correlations between asset classes:

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

This is applied during both accumulation and retirement phases. Diversification benefits are captured when correlations are less than +1, and risk is amplified when correlations are positive.

### 4. Stress Scenarios

For the first two years of retirement, you can optionally override the random returns with a deterministic crash:
- **Mild Crash**: -10% annual return for 2 years
- **Severe Crash**: -20% annual return for 2 years

This lets you test whether your plan can survive a bad start to retirement, which is historically the most dangerous period.

### 5. Pension Integration

If you have a pension, it is applied every year from `pension_start_age` onward:
- Gross pension is reduced by tax to get net pension
- Net pension first covers living expenses
- Any surplus is reinvested into the corpus
- Any shortfall must come from your portfolio withdrawals

Pension always helps the success rate because it reduces the burden on your investment corpus.

## How the Simulation Runs

For each of the 1,000–50,000 simulated paths:

1. Start with your current corpus and age.
2. Each year:
   - Add contributions (with annual growth) during the accumulation phase.
   - Add the one-time lumpsum at retirement.
   - Calculate expenses, inflated annually.
   - Calculate net pension (if applicable).
   - Determine how much must be withdrawn from the portfolio.
   - Apply tax to withdrawals.
   - Apply a stochastic return based on the chosen distribution and volatility.
   - Update the corpus.
   - If the corpus goes to zero while expenses are still unfunded, mark this path as a **failure**.
3. Repeat until `life_expectancy`.

At the end, aggregate all paths to compute:
- **Success rate**: % of paths where corpus never exhausted
- **Percentiles**: 5th, 25th, 50th (median), 75th, 95th corpus values at each year and at the end
- **Statistics**: median, mean, standard deviation, min, max of final corpus

## What the Results Mean

| Metric | Interpretation |
|---|---|
| **Probability of Success** | The % of simulated futures where you never run out of money. Higher is better. |
| **Median Final Corpus** | The middle outcome. 50% of futures do better, 50% do worse. |
| **5th Percentile** | A bad outcome. 95% of futures do better than this. |
| **95th Percentile** | A great outcome. Only 5% of futures do better. |

A wide gap between the 5th and 95th percentiles means your plan is highly sensitive to market luck. A narrow gap means outcomes are more predictable.

## Practical Guidance

- **Success rate below 50%** = high risk. Consider increasing contributions, reducing expenses, or delaying retirement.
- **Success rate above 80%** = generally comfortable, assuming your assumptions are realistic.
- **Median at ₹0** = your plan is break-even in the average market. Any bad luck and you run short.
- **95th percentile much higher than median** = there is huge upside in good markets, but also significant downside risk.

## Assumptions and Limitations

- Returns are independent year-to-year. Real markets have momentum and mean-reversion.
- Inflation is fixed at your input rate. In reality, inflation varies.
- Pension is assumed to grow at a fixed rate and be taxed at a fixed rate.
- Taxes on withdrawals are simplified and use a blended portfolio approach.
- The simulation does not model sequence-of-returns risk explicitly — but the percentile bands make it visible.

## Technical Notes

- **Seed**: Provide a random seed to reproduce the same simulation results exactly.
- **Simulation count**: More simulations = more stable results, but slower. 1,000–5,000 is usually sufficient.
- **Lognormal**: The default and recommended setting. It preserves the expected return while ensuring prices cannot go negative.
