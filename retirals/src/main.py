from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, model_validator, Field
from enum import Enum
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

class AdHocExpense(BaseModel):
    age: int = Field(..., gt=0, le=120, description="Age for the ad-hoc expense")
    amount: float = Field(..., ge=0, description="Amount of the ad-hoc expense")

class StressScenario(str, Enum):
    NORMAL = "Normal"
    MILD_CRASH = "Mild Crash (-10% for 2 yrs)"
    SEVERE_CRASH = "Severe Crash (-20% for 2 yrs)"

# Define the PlannerInputs model using Pydantic

class PlannerInputs(BaseModel):
    current_age: int = Field(43, gt=0, le=120)
    retirement_age: int = Field(54, gt=0, le=120)
    life_expectancy: int = Field(90, gt=0, le=120)
    current_annual_expenses: float = Field(1200000.00, gt=0, le=1e9)
    avg_inflation_rate: float = Field(0.06, ge=0, le=0.5)
    current_corpus: float = Field(4000000.00, ge=0, le=1e12)
    annual_contribution: float = Field(700000.00, ge=0, le=1e9)
    pre_retirement_return: float = Field(0.09, ge=-0.5, le=0.5)
    post_retirement_return: float = Field(0.08, ge=-0.5, le=0.5)
    contribution_increase: float = Field(0.01, ge=0, le=0.5)
    ltcg_exemption: float = Field(125000.00, ge=0, le=1e7)
    stress_scenario: StressScenario = StressScenario.NORMAL
    adhoc_expenses: list[AdHocExpense] = Field(default_factory=lambda: [
        AdHocExpense(age=58, amount=2500000.00),
        AdHocExpense(age=75, amount=1000000.00)
    ])
    # Portfolio Allocation
    allocation_equity: float = Field(0.60, ge=0, le=1.0)
    allocation_debt: float = Field(0.30, ge=0, le=1.0)
    allocation_arbitrage: float = Field(0.10, ge=0, le=1.0)
    # Equity sub-allocation (LTCG/STCG split)
    equity_ltcg_split: float = Field(0.70, ge=0, le=1.0)
    equity_stcg_split: float = Field(0.30, ge=0, le=1.0)
    # Tax rates by asset class
    tax_ltcg: float = Field(0.125, ge=0, le=1.0)
    tax_stcg: float = Field(0.20, ge=0, le=1.0)
    tax_debt: float = Field(0.20, ge=0, le=1.0)
    tax_arbitrage: float = Field(0.20, ge=0, le=1.0)

    @model_validator(mode="after")
    def validate_plan(self):
        if self.retirement_age <= self.current_age:
            raise ValueError("retirement_age must be greater than current_age")
        if self.life_expectancy < self.retirement_age:
            raise ValueError("life_expectancy must be greater than or equal to retirement_age")

        adhoc_ages = []
        for expense in self.adhoc_expenses:
            if not (self.current_age <= expense.age <= self.life_expectancy):
                raise ValueError(f"Ad-hoc expense age {expense.age} must be between current age and life expectancy.")
            if expense.age in adhoc_ages:
                raise ValueError(f"Duplicate ad-hoc expense age found: {expense.age}.")
            adhoc_ages.append(expense.age)

        # Validate portfolio allocation sums to ~1.0 (allow small rounding tolerance)
        allocation_total = self.allocation_equity + self.allocation_debt + self.allocation_arbitrage
        if abs(allocation_total - 1.0) > 0.01:
            raise ValueError("portfolio allocation (equity + debt + arbitrage) must sum to approximately 100%")
        
        # Validate equity sub-allocation
        equity_split_total = self.equity_ltcg_split + self.equity_stcg_split
        if abs(equity_split_total - 1.0) > 0.01:
            raise ValueError("equity sub-allocation (LTCG + STCG) must sum to approximately 100%")
        
        return self

def _calculate_retirement_logic(inputs: PlannerInputs):
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
        item.age: item.amount
        for item in adhoc_expenses
        if item.age is not None and item.amount is not None
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
        if age in ad_hoc_map:
            ad_hoc = ad_hoc_map[age] * ((1 + inputs.avg_inflation_rate) ** (age - inputs.current_age))

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
        else:
            gross_withdrawal = 0.0
            total_tax = 0.0
            required_after_tax_withdrawal = 0.0

        if not is_retired:
            return_rate = inputs.pre_retirement_return
        elif age < inputs.retirement_age + 2:
            if inputs.stress_scenario == StressScenario.MILD_CRASH:
                return_rate = -0.10
            elif inputs.stress_scenario == StressScenario.SEVERE_CRASH:
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
        (row["opening"] for row in projections if row["age"] == inputs.retirement_age), 0
    )
    final_corpus = round(projections[-1]["closing"]) if projections else 0
    
    if projections:
        # Find the age corresponding to the maximum closing corpus value
        peak_row = max(projections, key=lambda row: row["closing"])
        peak_age = peak_row["age"]
    else:
        peak_age = inputs.retirement_age

    retirement_ages = list(range(inputs.retirement_age, inputs.life_expectancy + 1))
    retirement_outflows = []
    for age in retirement_ages:
        # Calculate required after-tax withdrawal
        required_after_tax = inputs.current_annual_expenses * ((1 + inputs.avg_inflation_rate) ** (age - inputs.current_age))
        
        # Add adhoc expenses
        event_cost = 0
        if age in ad_hoc_map:
            event_cost = ad_hoc_map[age] * ((1 + inputs.avg_inflation_rate) ** (age - inputs.current_age))
        
        total_after_tax_needed = required_after_tax + event_cost
        retirement_outflows.append(total_after_tax_needed)

    # Calculate minimum corpus required by working backwards from life expectancy.
    # This ensures the final corpus is >= 0.
    minimum_corpus_required = 0.0
    for age in reversed(range(inputs.retirement_age, inputs.life_expectancy + 1)):
        # Determine the correct return rate for this age, mirroring the forward projection
        if age < inputs.retirement_age + 2:
            if inputs.stress_scenario == StressScenario.MILD_CRASH:
                return_rate = -0.10
            elif inputs.stress_scenario == StressScenario.SEVERE_CRASH:
                return_rate = -0.20
            else:
                return_rate = inputs.post_retirement_return
        else:
            return_rate = inputs.post_retirement_return

        # Calculate this year's outflows, including ad-hoc expenses, exactly as in the forward projection
        elapsed_years = age - inputs.current_age
        required_after_tax_withdrawal = inputs.current_annual_expenses * ((1 + inputs.avg_inflation_rate) ** elapsed_years)
        ad_hoc = ad_hoc_map.get(age, 0.0) * ((1 + inputs.avg_inflation_rate) ** elapsed_years)

        # Calculate gross (pre-tax) withdrawal for regular expenses
        gross_withdrawal = required_after_tax_withdrawal / (1.0 - blended_tax_rate) if blended_tax_rate < 1.0 else required_after_tax_withdrawal

        # Total outflow for the year is the sum of grossed-up expenses and ad-hoc costs
        total_outflow_for_year = gross_withdrawal + ad_hoc

        # The corpus required at the start of the year is the sum of:
        # 1. The total outflow for the current year.
        # 2. The present value of the corpus required at the start of the *next* year.
        minimum_corpus_required = total_outflow_for_year + (minimum_corpus_required / (1 + return_rate))

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

@app.post("/calculate")
def calculate_retirement(inputs: PlannerInputs):
    try:
        return _calculate_retirement_logic(inputs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/")
async def read_index():
    static_file = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
    return FileResponse(static_file)


if __name__ == "__main__":
    port = int(getenv("PORT", 20080))
    print(f"Starting Parity Retirement Planner Server...")
    print(f"  - Access the planner at http://localhost:{port}/")
    uvicorn.run(app, host="0.0.0.0", port=port)