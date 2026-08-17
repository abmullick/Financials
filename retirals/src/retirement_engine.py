from models import PlannerInputs
from stress_engine import get_return_rate

def _calculate_gross_withdrawal(net_required: float, inputs: PlannerInputs, tax_portions: dict) -> tuple[float, float]:
    """
    Calculates the gross withdrawal required to meet a net (after-tax) amount.

    This function implements a piecewise calculation to correctly handle the annual
    LTCG exemption, which applies only to gains exceeding the threshold.

    Args:
        net_required: The after-tax amount needed.
        inputs: The PlannerInputs object.
        tax_portions: A dictionary with pre-calculated tax portions.

    Returns:
        A tuple containing (gross_withdrawal, total_tax).
    """
    if net_required <= 0:
        return 0.0, 0.0

    # Case 1: Withdrawal is small, LTCG component is below the exemption limit.
    # Tax is calculated only on non-LTCG portions of the withdrawal.
    # G = N / (1 - other_tax_rate)
    other_tax_rate = tax_portions["other_blended_rate"]
    gross_withdrawal_case1 = net_required / (1.0 - other_tax_rate) if other_tax_rate < 1.0 else float('inf')

    # Determine if we need to consider Case 2 (where LTCG tax applies).
    # This happens if the LTCG component of the withdrawal exceeds the exemption.
    ltcg_portion_of_withdrawal = gross_withdrawal_case1 * tax_portions["equity_ltcg_portion"]

    if ltcg_portion_of_withdrawal <= inputs.ltcg_exemption:
        # We are in Case 1. The LTCG component is fully exempt.
        gross_withdrawal = gross_withdrawal_case1
    else:
        # Case 2: Withdrawal is large, LTCG component exceeds the exemption limit.
        # The full blended tax rate applies, but we get a fixed tax credit from the exemption.
        # G = (N - (Exemption * LTCG_Tax_Rate)) / (1 - Full_Blended_Rate)
        blended_rate_no_exemption = tax_portions["blended_rate_no_exemption"]
        ltcg_tax_impact_from_exemption = inputs.ltcg_exemption * inputs.tax_ltcg

        if blended_rate_no_exemption < 1.0:
            gross_withdrawal = (net_required - ltcg_tax_impact_from_exemption) / (1.0 - blended_rate_no_exemption)
        else:
            gross_withdrawal = float('inf')

    gross_withdrawal = max(0, gross_withdrawal)
    total_tax = gross_withdrawal - net_required
    return gross_withdrawal, total_tax


def run_projection(inputs: PlannerInputs):

    projections = []
    opening_corpus = inputs.current_corpus
    total_contributions = 0.0

    ad_hoc_map = {item.age: item.amount for item in inputs.adhoc_expenses or []}

    # Pre-calculate portfolio portions for tax calculation
    equity_ltcg_portion = inputs.allocation_equity * inputs.equity_ltcg_split
    equity_stcg_portion = inputs.allocation_equity * inputs.equity_stcg_split
    debt_portion = inputs.allocation_debt
    arbitrage_portion = inputs.allocation_arbitrage

    tax_portions = {
        "equity_ltcg_portion": equity_ltcg_portion,
        "blended_rate_no_exemption": (equity_ltcg_portion * inputs.tax_ltcg) + (equity_stcg_portion * inputs.tax_stcg) + (debt_portion * inputs.tax_debt) + (arbitrage_portion * inputs.tax_arbitrage),
        "other_blended_rate": (equity_stcg_portion * inputs.tax_stcg) + (debt_portion * inputs.tax_debt) + (arbitrage_portion * inputs.tax_arbitrage)
    }

    for age in range(inputs.current_age, inputs.life_expectancy + 1):
        elapsed_years = age - inputs.current_age
        is_retired = age >= inputs.retirement_age

        contribution = 0.0
        if not is_retired:
            contribution = inputs.annual_contribution * ((1 + inputs.contribution_increase) ** elapsed_years)
            total_contributions += contribution

        required_after_tax_withdrawal = 0.0
        if is_retired:
            required_after_tax_withdrawal = inputs.current_annual_expenses * ((1 + inputs.avg_inflation_rate) ** elapsed_years)

        ad_hoc = 0.0
        if age in ad_hoc_map:
            ad_hoc = ad_hoc_map[age] * ((1 + inputs.avg_inflation_rate) ** elapsed_years)

        gross_withdrawal = 0.0
        total_tax = 0.0
        if is_retired and (required_after_tax_withdrawal > 0 or ad_hoc > 0):
            net_required = required_after_tax_withdrawal + ad_hoc
            gross_withdrawal, total_tax = _calculate_gross_withdrawal(net_required, inputs, tax_portions)

        return_rate = get_return_rate(age, inputs)

        # This is an "Annuity Due" model (beginning-of-period contributions)
        # Contributions made at the start of the year get a full year's return.
        net_for_return = opening_corpus + contribution - gross_withdrawal
        returns = net_for_return * return_rate
        closing_corpus = net_for_return + returns

        projections.append({
            "year": elapsed_years + 1, "age": age,
            "opening": round(opening_corpus, 2),
            "contribution": round(contribution, 2),
            "withdrawal": round(gross_withdrawal, 2),
            "withdrawal_tax": round(total_tax, 2),
            "withdrawal_after_tax": round(required_after_tax_withdrawal, 2),
            "ad_hoc": round(ad_hoc, 2),
            "return": round(returns, 2),
            "closing": round(closing_corpus, 2)
        })
        opening_corpus = closing_corpus

    # Calculate final metrics
    corpus_at_retirement = next((p["opening"] for p in projections if p["age"] == inputs.retirement_age), 0)
    final_corpus = projections[-1]["closing"] if projections else 0

    peak_age = inputs.current_age
    if projections:
        # Find the row with the maximum closing corpus to determine the true peak age
        peak_age = max(projections, key=lambda row: row["closing"])["age"]

    minimum_corpus_required = _calculate_minimum_corpus(inputs, ad_hoc_map)
    
    gap_analysis = _calculate_gap_analysis(inputs, corpus_at_retirement, minimum_corpus_required)

    return {
        "metrics": {
            "corpus_at_retirement": round(corpus_at_retirement, 2),
            "final_corpus": round(final_corpus, 2),
            "years_in_retirement": inputs.life_expectancy - inputs.retirement_age,
            "retirement_projection_points": (inputs.life_expectancy - inputs.retirement_age) + 1, # This is correct
            "peak_age": peak_age,
            "total_contributions": round(total_contributions, 2),
            "minimum_corpus_required": round(minimum_corpus_required, 2),
            **gap_analysis,  # Merge gap analysis metrics
            # Merge goal-seek return metrics
            **_solve_for_required_returns(inputs, corpus_at_retirement, minimum_corpus_required, ad_hoc_map),
        },
        "projections": projections
    }

def _calculate_minimum_corpus(inputs: PlannerInputs, ad_hoc_map: dict) -> float:
    """
    Calculates the minimum corpus required at retirement by working backwards
    from life expectancy.
    """
    minimum_corpus_required = 0.0

    # Pre-calculate portfolio portions for tax calculation
    equity_ltcg_portion = inputs.allocation_equity * inputs.equity_ltcg_split
    equity_stcg_portion = inputs.allocation_equity * inputs.equity_stcg_split
    debt_portion = inputs.allocation_debt
    arbitrage_portion = inputs.allocation_arbitrage

    tax_portions = {
        "equity_ltcg_portion": equity_ltcg_portion,
        "blended_rate_no_exemption": (equity_ltcg_portion * inputs.tax_ltcg) + (equity_stcg_portion * inputs.tax_stcg) + (debt_portion * inputs.tax_debt) + (arbitrage_portion * inputs.tax_arbitrage),
        "other_blended_rate": (equity_stcg_portion * inputs.tax_stcg) + (debt_portion * inputs.tax_debt) + (arbitrage_portion * inputs.tax_arbitrage)
    }

    for age in reversed(range(inputs.retirement_age, inputs.life_expectancy + 1)):
        return_rate = get_return_rate(age, inputs)

        # Calculate this year's outflows, exactly as in the forward projection
        elapsed_years = age - inputs.current_age
        required_after_tax_withdrawal = inputs.current_annual_expenses * ((1 + inputs.avg_inflation_rate) ** elapsed_years)
        
        ad_hoc = 0.0
        if age in ad_hoc_map:
            ad_hoc = ad_hoc_map[age] * ((1 + inputs.avg_inflation_rate) ** elapsed_years)

        # Total after-tax outflow needed for the year
        total_net_outflow = required_after_tax_withdrawal + ad_hoc

        # Calculate the gross (pre-tax) outflow required to generate the net outflow
        total_gross_outflow = 0.0
        total_gross_outflow, _ = _calculate_gross_withdrawal(total_net_outflow, inputs, tax_portions)

        # This logic correctly inverts the forward projection's "beginning-of-period" withdrawal model.
        # The corpus at the start of the year must be enough to cover this year's outflow,
        # and the remainder must be enough to grow into the corpus needed for the start of the next year.
        # Corpus_Start = Outflow + PV(Corpus_Next_Year)
        minimum_corpus_required = total_gross_outflow + (minimum_corpus_required / (1 + return_rate))

    return minimum_corpus_required

def _calculate_gap_analysis(inputs: PlannerInputs, corpus_at_retirement: float, minimum_corpus_required: float) -> dict:
    """
    Calculates retirement readiness and the investment required to close any gap.
    """
    readiness_percent = 0.0
    if minimum_corpus_required > 0:
        readiness_percent = (corpus_at_retirement / minimum_corpus_required) * 100

    gap = minimum_corpus_required - corpus_at_retirement
    target_annual_contribution = inputs.annual_contribution

    if gap > 0:
        # Use the Future Value of a Growing Annuity DUE formula to match the projection engine's
        # beginning-of-period contribution model.
        # Formula: FV = P * (1+r) * [((1+r)^n - (1+g)^n) / (r-g)]
        # Solved for P (first year's payment): P = FV / ((1+r) * [((1+r)^n - (1+g)^n) / (r-g)])
        
        n = inputs.retirement_age - inputs.current_age  # Number of years
        r = inputs.pre_retirement_return               # Annual return rate
        g = inputs.contribution_increase               # Annual growth rate of contribution

        if n > 0:
            # Handle the special case where r == g
            if abs(r - g) < 1e-9:
                # Simplified formula for r=g: FV = P * n * (1+r)^n
                fv_factor = n * ((1 + r) ** n)
            else:
                # Standard formula for r != g, adjusted for beginning-of-period payments
                fv_factor = (1 + r) * ((((1 + r) ** n) - ((1 + g) ** n)) / (r - g))

            if fv_factor > 0:
                # This is the total additional investment required in the *first year*
                additional_investment = gap / fv_factor
                target_annual_contribution += additional_investment

    return {
        "readiness_percent": round(readiness_percent, 2),
        "gap_at_retirement": round(gap, 2),
        "target_annual_contribution_for_gap": round(target_annual_contribution, 2)
    }

def _solve_for_required_returns(inputs: PlannerInputs, corpus_at_retirement: float, minimum_corpus_required: float, ad_hoc_map: dict) -> dict:
    """
    Performs a goal-seek analysis to find the pre- and post-retirement returns
    required to achieve 100% retirement readiness.
    """
    required_pre_ret_return = inputs.pre_retirement_return
    required_post_ret_return = inputs.post_retirement_return
    gap = minimum_corpus_required - corpus_at_retirement

    if gap > 0:
        # --- 1. Solve for Required Pre-Retirement Return ---
        def get_future_corpus(rate):
            # Calculates corpus at retirement for a given pre-retirement return rate
            n = inputs.retirement_age - inputs.current_age
            g = inputs.contribution_increase
            
            fv_current_corpus = inputs.current_corpus * ((1 + rate) ** n)
            
            if abs(rate - g) < 1e-9:
                fv_factor = n * ((1 + rate) ** n)
            else:
                fv_factor = (1 + rate) * ((((1 + rate) ** n) - ((1 + g) ** n)) / (rate - g))
            
            fv_contributions = inputs.annual_contribution * fv_factor
            return fv_current_corpus + fv_contributions

        # Bisection method to find the rate
        low, high = inputs.pre_retirement_return, 0.50  # Search up to 50%
        for _ in range(30): # 30 iterations for high precision
            mid = (low + high) / 2
            if get_future_corpus(mid) < minimum_corpus_required:
                low = mid
            else:
                high = mid
        if high < 0.50: # If a solution was found
            required_pre_ret_return = high

        # --- 2. Solve for Required Post-Retirement Return ---
        def get_min_corpus(rate):
            # Calculates min_corpus_required for a given post-retirement return rate
            # This is a simplified version of the main _calculate_minimum_corpus function
            return _calculate_minimum_corpus(inputs.copy(update={"post_retirement_return": rate}), ad_hoc_map)

        # Bisection method to find the rate
        low, high = inputs.post_retirement_return, 0.50 # Search up to 50%
        for _ in range(30):
            mid = (low + high) / 2
            if get_min_corpus(mid) > corpus_at_retirement:
                low = mid
            else:
                high = mid
        if high < 0.50: # If a solution was found
            required_post_ret_return = high

    return {
        "required_pre_retirement_return": round(required_pre_ret_return * 100, 2),
        "required_post_retirement_return": round(required_post_ret_return * 100, 2)
    }