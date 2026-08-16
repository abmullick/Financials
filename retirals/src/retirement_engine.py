from models import PlannerInputs
from tax_engine import calculate_blended_tax_rate
from stress_engine import get_return_rate

def run_projection(inputs: PlannerInputs):
    blended_tax_rate = calculate_blended_tax_rate(inputs)

    projections = []
    opening_corpus = inputs.current_corpus
    total_contributions = 0.0

    ad_hoc_map = {item.age: item.amount for item in inputs.adhoc_expenses or []}

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
        if is_retired and required_after_tax_withdrawal > 0:
            if blended_tax_rate < 1.0:
                gross_withdrawal = required_after_tax_withdrawal / (1.0 - blended_tax_rate)
                total_tax = gross_withdrawal - required_after_tax_withdrawal
            else:
                gross_withdrawal = required_after_tax_withdrawal
        
        return_rate = get_return_rate(age, inputs)

        # This is an "Annuity Due" model (beginning-of-period contributions)
        # Contributions made at the start of the year get a full year's return.
        net_for_return = opening_corpus + contribution - gross_withdrawal - ad_hoc
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
    
    peak_age = inputs.retirement_age
    if projections:
        peak_row = max(projections, key=lambda row: row["closing"])
        peak_age = peak_row["age"]

    minimum_corpus_required = _calculate_minimum_corpus(inputs, ad_hoc_map, blended_tax_rate)
    
    gap_analysis = _calculate_gap_analysis(inputs, corpus_at_retirement, minimum_corpus_required)

    return {
        "metrics": {
            "corpus_at_retirement": round(corpus_at_retirement, 2),
            "final_corpus": round(final_corpus, 2),
            "years_in_retirement": inputs.life_expectancy - inputs.retirement_age,
            "peak_age": peak_age,
            "total_contributions": round(total_contributions, 2),
            "minimum_corpus_required": round(minimum_corpus_required, 2),
            **gap_analysis,  # Merge gap analysis metrics
            # Merge goal-seek return metrics
            **_solve_for_required_returns(inputs, corpus_at_retirement, minimum_corpus_required, ad_hoc_map, blended_tax_rate),
        },
        "projections": projections
    }

def _calculate_minimum_corpus(inputs: PlannerInputs, ad_hoc_map: dict, blended_tax_rate: float) -> float:
    """
    Calculates the minimum corpus required at retirement by working backwards
    from life expectancy.
    """
    minimum_corpus_required = 0.0
    for age in reversed(range(inputs.retirement_age, inputs.life_expectancy + 1)):
        return_rate = get_return_rate(age, inputs)

        # Calculate this year's outflows, exactly as in the forward projection
        elapsed_years = age - inputs.current_age
        required_after_tax_withdrawal = inputs.current_annual_expenses * ((1 + inputs.avg_inflation_rate) ** elapsed_years)
        
        ad_hoc = 0.0
        if age in ad_hoc_map:
            ad_hoc = ad_hoc_map[age] * ((1 + inputs.avg_inflation_rate) ** elapsed_years)

        # Calculate gross (pre-tax) withdrawal for regular expenses
        gross_withdrawal = 0.0
        if required_after_tax_withdrawal > 0:
            if blended_tax_rate < 1.0:
                gross_withdrawal = required_after_tax_withdrawal / (1.0 - blended_tax_rate)
            else:
                gross_withdrawal = required_after_tax_withdrawal

        # Total outflow for the year is the sum of grossed-up expenses and ad-hoc costs
        total_outflow_for_year = gross_withdrawal + ad_hoc

        # This logic correctly inverts the forward projection's "beginning-of-period" withdrawal model.
        # The corpus at the start of the year must be enough to cover this year's outflow,
        # and the remainder must be enough to grow into the corpus needed for the start of the next year.
        # Corpus_Start = Outflow + PV(Corpus_Next_Year)
        # Corpus_Start = total_outflow_for_year + (minimum_corpus_required / (1 + return_rate))
        minimum_corpus_required = total_outflow_for_year + (minimum_corpus_required / (1 + return_rate))

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

def _solve_for_required_returns(inputs: PlannerInputs, corpus_at_retirement: float, minimum_corpus_required: float, ad_hoc_map: dict, blended_tax_rate: float) -> dict:
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
            temp_inputs = inputs.copy(update={"post_retirement_return": rate})
            min_corpus = 0.0
            for age in reversed(range(temp_inputs.retirement_age, temp_inputs.life_expectancy + 1)):
                # Simplified get_return_rate logic for post-retirement
                return_rate = rate if age >= temp_inputs.retirement_age + 2 else get_return_rate(age, temp_inputs)
                
                elapsed_years = age - temp_inputs.current_age
                req_withdrawal = temp_inputs.current_annual_expenses * ((1 + temp_inputs.avg_inflation_rate) ** elapsed_years)
                ad_hoc = ad_hoc_map.get(age, 0.0) * ((1 + temp_inputs.avg_inflation_rate) ** elapsed_years)
                gross_withdrawal = req_withdrawal / (1.0 - blended_tax_rate) if blended_tax_rate < 1.0 else req_withdrawal
                total_outflow = gross_withdrawal + ad_hoc
                min_corpus = total_outflow + (min_corpus / (1 + return_rate))
            return min_corpus

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