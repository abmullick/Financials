from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, model_validator
import uvicorn
import os
from os import getenv

# Start the FastAPI application 

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "assets")), name="assets")

# Define the PlannerInputs model using Pydantic

class PlannerInputs(BaseModel):
    current_age: int = 43
    retirement_age: int = 54
    life_expectancy: int = 90
    current_annual_expenses: float = 1200000.00
    avg_inflation_rate: float = 0.06
    current_corpus: float = 4000000.00
    annual_contribution: float = 700000.00
    pre_retirement_return: float = 0.16
    post_retirement_return: float = 0.15
    contribution_increase: float = 0.01
    ltcg_exemption: float = 125000.00
    stress_scenario: str = "Normal"
    adhoc_expenses: list[dict] = [{"age": 58, "amount": 2500000.00}, {"age": 75, "amount": 1000000.00}]
    # Portfolio Allocation
    allocation_equity: float = 0.60
    allocation_debt: float = 0.30
    allocation_arbitrage: float = 0.10
    # Equity sub-allocation (LTCG/STCG split)
    equity_ltcg_split: float = 0.70
    equity_stcg_split: float = 0.30
    # Tax rates by asset class
    tax_ltcg: float = 0.125
    tax_stcg: float = 0.20
    tax_debt: float = 0.20
    tax_arbitrage: float = 0.20

    @model_validator(mode="after")
    def validate_plan(self):
        if self.current_age <= 0:
            raise ValueError("current_age must be greater than zero")
        if self.retirement_age <= self.current_age:
            raise ValueError("retirement_age must be greater than current_age")
        if self.life_expectancy < self.retirement_age:
            raise ValueError("life_expectancy must be greater than or equal to retirement_age")
        if self.current_annual_expenses <= 0:
            raise ValueError("current_annual_expenses must be positive")
        if self.current_corpus < 0:
            raise ValueError("current_corpus cannot be negative")
        if self.annual_contribution < 0:
            raise ValueError("annual_contribution cannot be negative")
        if not 0 <= self.avg_inflation_rate < 1:
            raise ValueError("avg_inflation_rate must be between 0 and 1")
        if not 0 <= self.pre_retirement_return < 1:
            raise ValueError("pre_retirement_return must be between 0 and 1")
        if not 0 <= self.post_retirement_return < 1:
            raise ValueError("post_retirement_return must be between 0 and 1")
        # Validate portfolio allocation sums to ~1.0 (allow small rounding tolerance)
        allocation_total = self.allocation_equity + self.allocation_debt + self.allocation_arbitrage
        if abs(allocation_total - 1.0) > 0.01:
            raise ValueError("portfolio allocation (equity + debt + arbitrage) must sum to approximately 100%")
        # Validate equity sub-allocation
        equity_split_total = self.equity_ltcg_split + self.equity_stcg_split
        if abs(equity_split_total - 1.0) > 0.01:
            raise ValueError("equity sub-allocation (LTCG + STCG) must sum to approximately 100%")
        # Validate tax rates are between 0 and 1
        for tax_rate_value in [self.tax_ltcg, self.tax_stcg, self.tax_debt, self.tax_arbitrage]:
            if not 0 <= tax_rate_value <= 1:
                raise ValueError("all tax rates must be between 0 and 1")
        return self

@app.post("/calculate")
def calculate_retirement(inputs: PlannerInputs):
    if not inputs:
        raise HTTPException(status_code=400, detail="Request body is required")

    # Calculate blended effective tax rate based on portfolio allocation
    # Equity is split between LTCG and STCG
    equity_ltcg_portion = inputs.allocation_equity * inputs.equity_ltcg_split
    equity_stcg_portion = inputs.allocation_equity * inputs.equity_stcg_split
    
    blended_tax_rate = (
        equity_ltcg_portion * inputs.tax_ltcg +
        equity_stcg_portion * inputs.tax_stcg +
        inputs.allocation_debt * inputs.tax_debt +
        inputs.allocation_arbitrage * inputs.tax_arbitrage
    )

    projections = []
    opening_corpus = inputs.current_corpus
    total_contributions = 0.0

    adhoc_expenses = inputs.adhoc_expenses or []
    ad_hoc_map = {
        int(item["age"]): float(item["amount"])
        for item in adhoc_expenses
        if isinstance(item, dict) and item.get("age") is not None and item.get("amount") is not None
    }

    for age in range(inputs.current_age, inputs.life_expectancy + 1):
        elapsed_years = age - inputs.current_age
        is_retired = age >= inputs.retirement_age

        if not is_retired:
            contribution = inputs.annual_contribution * ((1 + inputs.contribution_increase) ** elapsed_years)
            total_contributions += contribution
        else:
            contribution = 0.0

        # Calculate required withdrawal amount (pre-tax)
        if is_retired:
            required_after_tax_withdrawal = inputs.current_annual_expenses * ((1 + inputs.avg_inflation_rate) ** elapsed_years)
        else:
            required_after_tax_withdrawal = 0.0

        ad_hoc = 0.0
        for event_age, event_amount in ad_hoc_map.items():
            if age == event_age:
                ad_hoc += event_amount * ((1 + inputs.avg_inflation_rate) ** (age - inputs.current_age))

        # Calculate gross withdrawal and tax deduction
        if is_retired and required_after_tax_withdrawal > 0:
            # Gross withdrawal = required_after_tax / (1 - effective_tax_rate)
            # This ensures: gross_withdrawal * (1 - tax_rate) = required_after_tax_withdrawal
            if blended_tax_rate < 1.0:
                gross_withdrawal = required_after_tax_withdrawal / (1.0 - blended_tax_rate)
                total_tax = gross_withdrawal - required_after_tax_withdrawal
            else:
                # Edge case: if tax rate is 100%, withdrawal cannot meet requirement
                gross_withdrawal = required_after_tax_withdrawal
                total_tax = 0.0
            
            # Break down tax by asset class for reporting (optional, for transparency)
            tax_by_ltcg = gross_withdrawal * equity_ltcg_portion * inputs.tax_ltcg
            tax_by_stcg = gross_withdrawal * equity_stcg_portion * inputs.tax_stcg
            tax_by_debt = gross_withdrawal * inputs.allocation_debt * inputs.tax_debt
            tax_by_arbitrage = gross_withdrawal * inputs.allocation_arbitrage * inputs.tax_arbitrage
        else:
            gross_withdrawal = 0.0
            total_tax = 0.0
            required_after_tax_withdrawal = 0.0

        if not is_retired:
            return_rate = inputs.pre_retirement_return
        elif age < inputs.retirement_age + 2:
            if inputs.stress_scenario == "Mild Crash (-10% for 2 yrs)":
                return_rate = -0.10
            elif inputs.stress_scenario == "Severe Crash (-20% for 2 yrs)":
                return_rate = -0.20
            else:
                return_rate = inputs.post_retirement_return
        else:
            return_rate = inputs.post_retirement_return

        # Net amount available for returns calculation after all outflows
        net_for_return = opening_corpus + contribution - gross_withdrawal - ad_hoc
        returns = net_for_return * return_rate
        closing_corpus = opening_corpus + contribution - gross_withdrawal - ad_hoc + returns

        projections.append({
            "year": elapsed_years + 1,
            "age": age,
            "opening": round(opening_corpus, 2),
            "contribution": round(contribution, 2),
            "withdrawal": round(gross_withdrawal, 2),  # Gross withdrawal
            "withdrawal_tax": round(total_tax, 2),  # Tax deducted
            "withdrawal_after_tax": round(required_after_tax_withdrawal, 2),  # Net to client
            "ad_hoc": round(ad_hoc, 2),
            "return": round(returns, 2),
            "closing": round(closing_corpus, 2)
        })

        opening_corpus = closing_corpus

    corpus_at_retirement = next(
        row["opening"] for row in projections if row["age"] == inputs.retirement_age
    )
    final_corpus = round(projections[-1]["closing"])
    peak_age = next(
        (
            row["age"]
            for row in projections
            if row["age"] >= inputs.retirement_age and row["closing"] < row["opening"]
        ),
        inputs.life_expectancy,
    )

    retirement_ages = list(range(inputs.retirement_age, inputs.life_expectancy + 1))
    retirement_outflows = []
    for age in retirement_ages:
        # Calculate required after-tax withdrawal
        required_after_tax = inputs.current_annual_expenses * ((1 + inputs.avg_inflation_rate) ** (age - inputs.current_age))
        
        # Add adhoc expenses
        event_cost = sum(
            amount * ((1 + inputs.avg_inflation_rate) ** (age - inputs.current_age))
            for event_age, amount in ad_hoc_map.items()
            if event_age == age
        )
        
        total_after_tax_needed = required_after_tax + event_cost
        retirement_outflows.append(total_after_tax_needed)

    if retirement_ages:
        pv_outflows = sum(
            outflow / ((1 + inputs.post_retirement_return) ** (age - inputs.retirement_age))
            for age, outflow in zip(retirement_ages, retirement_outflows)
        )
        last_outflow = retirement_outflows[-1]
        terminal_value = last_outflow * (1 + inputs.post_retirement_return) / inputs.post_retirement_return
        pv_terminal = terminal_value / ((1 + inputs.post_retirement_return) ** (inputs.life_expectancy - inputs.retirement_age + 1))
        minimum_corpus_required = pv_outflows + pv_terminal
    else:
        minimum_corpus_required = 0.0

    return {
        "metrics": {
            "corpus_at_retirement": round(corpus_at_retirement, 2),
            "final_corpus": round(final_corpus, 2),
            "years_in_retirement": inputs.life_expectancy - inputs.retirement_age,
            "peak_age": peak_age,
            "total_contributions": round(total_contributions, 2),
            "minimum_corpus_required": round(minimum_corpus_required, 2)
        },
        "projections": projections
    }

@app.get("/")
async def read_index():
    static_file = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
    return FileResponse(static_file)

if __name__ == "__main__":
    port = int(getenv("PORT", 20080))
    print(f"Starting Parity Retirement Planner Server at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)