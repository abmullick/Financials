from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

app = FastAPI()
app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "assets")), name="assets")

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
    ltcg_tax_rate: float = 0.125
    ltcg_exemption: float = 125000.00
    gain_ratio: float = 0.60
    stress_scenario: str = "Normal"
    adhoc_expenses: list[dict] = [{"age": 58, "amount": 2500000.00}, {"age": 75, "amount": 1000000.00}]

@app.post("/calculate")
def calculate_retirement(inputs: PlannerInputs):
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

        if is_retired:
            withdrawal = inputs.current_annual_expenses * ((1 + inputs.avg_inflation_rate) ** elapsed_years)
        else:
            withdrawal = 0.0

        ad_hoc = 0.0
        for event_age, event_amount in ad_hoc_map.items():
            if age == event_age:
                ad_hoc += event_amount * ((1 + inputs.avg_inflation_rate) ** (age - inputs.current_age))

        if is_retired and withdrawal > 0:
            estimated_gains = withdrawal * inputs.gain_ratio
            taxable_gain = max(0.0, estimated_gains - inputs.ltcg_exemption)
            ltcg_tax = taxable_gain * inputs.ltcg_tax_rate
        else:
            ltcg_tax = 0.0

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

        net_for_return = opening_corpus + contribution - withdrawal - ad_hoc - ltcg_tax
        returns = net_for_return * return_rate
        closing_corpus = opening_corpus + contribution - withdrawal - ad_hoc - ltcg_tax + returns

        projections.append({
            "year": elapsed_years + 1,
            "age": age,
            "opening": round(opening_corpus, 2),
            "contribution": round(contribution, 2),
            "withdrawal": round(withdrawal, 2),
            "ad_hoc": round(ad_hoc, 2),
            "ltcg_tax": round(ltcg_tax, 2),
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
        annual_expense = inputs.current_annual_expenses * ((1 + inputs.avg_inflation_rate) ** (age - inputs.current_age))
        event_cost = sum(
            amount * ((1 + inputs.avg_inflation_rate) ** (age - inputs.current_age))
            for event_age, amount in ad_hoc_map.items()
            if event_age == age
        )
        retirement_outflows.append(annual_expense + event_cost)

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
    print("Starting Parity Retirement Planner Server at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=20080)