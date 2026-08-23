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

**Lognormal (default)**
- The standard choice for modeling asset prices.
- It cannot produce returns below -100%, which is physically correct — you cannot lose more than 100% of your money.
- The simulation calibrates it so that its expected *arithmetic* return equals your selected pre- or post-retirement return.

**Normal**
- Simpler, but can theoretically produce returns below -100%, implying a negative portfolio value.
- Mathematically convenient but less realistic for long horizons.

### 3. Portfolio Blending

Your allocation across equity, debt, and arbitrage is used to calculate one **portfolio volatility** each year with a covariance-based formula that accounts for correlations between asset classes:

In plain language, the calculation asks two questions:

- How volatile is each part of the portfolio on its own?
- Do those parts usually rise and fall together, or do they partly offset one another?

Putting money in more than one asset class can reduce overall volatility when their returns do not move in lockstep. It is not a guarantee against losses: when assets move together, diversification offers less protection.

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

Correlation ranges from `-1` to `+1`:

- `+1` means two asset classes always move together, so there is no diversification benefit between them.
- `0` means they move independently.
- A value below `0` means they tend to move in opposite directions, which can reduce portfolio volatility.

This calculation is applied during both accumulation and retirement. Positive correlation does not automatically increase risk; it reduces the diversification benefit relative to a lower correlation.

The current model then draws a single return for the whole portfolio. It does **not** generate separate asset-class return paths, track individual asset balances, or model rebalancing. Your pre- and post-retirement return assumptions determine the portfolio's expected return; allocation and correlations determine its volatility (and allocation also affects the simplified withdrawal-tax calculation).

Correlation inputs should be realistic as a group. Some individually valid correlations can form an invalid correlation matrix; if that happens, the calculated variance is floored at zero, which can understate risk.

### 4. Stress Scenarios

For the first two years of retirement, you can optionally override the random returns with a deterministic crash:
- **Mild Crash**: -10% annual return for 2 years
- **Severe Crash**: -20% annual return for 2 years

This lets you test whether your plan can survive a bad start to retirement, which is historically the most dangerous period.

### 5. Pension Integration

If you have a pension, it is applied every year from `pension_start_age` onward:
- Gross pension is reduced by tax to get net pension
- Net pension first covers living expenses
- Any surplus is reinvested into the corpus only when **Reinvest pension surplus** is enabled
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
- **Funding probability by age**: for each age, the % of simulations where expenses were fully funded
- **Failure age percentiles**: for failed paths, the distribution of ages at which corpus first exhausts
- **Final corpus histogram**: 20-bin histogram of final corpus values
- **Retirement age sensitivity**: success rates and median corpus for alternative retirement ages
- **Recommendations**: plain-language suggestions based on the simulation output

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
- **Success rate above 80%** = a useful starting point, but not automatically comfortable. Choose a target that reflects your risk tolerance, flexibility in spending, and ability to earn income or adjust plans.
- **Median at ₹0** = your plan is break-even in the average market. Any bad luck and you run short.
- **95th percentile much higher than median** = there is huge upside in good markets, but also significant downside risk.
- **Funding probability by age** = use this to see exactly when your plan becomes fragile. If the line drops below 75% at age 72, that's a signal to shore up the plan before then.
- **Retirement age sensitivity** = if a 2-year delay raises success rate from 48% to 82%, that's a high-leverage improvement to consider.
- **Recommendations** = the engine suggests concrete actions such as increasing contributions or delaying retirement, but treat these as starting points rather than personalized advice.

## Assumptions and Limitations

- Returns are independent year-to-year. Real markets have momentum and mean-reversion.
- Inflation is fixed at your input rate. In reality, inflation varies.
- Pension is assumed to grow at a fixed rate and be taxed at a fixed rate.
- Taxes on withdrawals are simplified and use a blended portfolio approach.
- The simulation models sequence-of-returns risk: each path has a different ordered sequence of annual returns, while withdrawals continue through poor markets. It does not model serial market behavior such as momentum or mean reversion.
- Asset-class returns, changing allocations, rebalancing, and changing tax lots are not modeled separately.
- The lognormal distribution prevents a return below -100%, but the configured volatility is used as a log-return volatility parameter. The realised arithmetic-return volatility therefore will not exactly equal the input value.
- Results are planning estimates, not financial, tax, or investment advice.

## Technical Notes

- **Seed**: Provide a random seed to reproduce the same simulation results exactly.
- **Simulation count**: More simulations = more stable results, but slower. 1,000–5,000 is usually sufficient.
- **Lognormal**: The default setting. It preserves the configured expected arithmetic return while ensuring portfolio values cannot become negative solely because of a return below -100%.
